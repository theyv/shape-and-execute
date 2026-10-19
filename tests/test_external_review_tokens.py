"""Tests of [REVIEW-TOKENS]: a review run through the printed COMMAND records its tokens at collect.
[RECORD-PRIVACY]: collect then deletes the harness output, usage or not.

Run from the repository root:  /usr/bin/python3 -m unittest discover -s tests
The fake `codex` and `claude` print small hand-made outputs in the shapes the harnesses use.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from saetest import Sandbox, SaeTestCase, dispatch_workspace  # noqa: E402

REVIEW_TEXT = "---\ntarget: ONE\nverdict: pass\n---\n\n# Review\n\nLooks right.\n"

# `codex exec --json`: JSONL events on stdout, two turns and a harmless error item; `-o` gets the last message.
CODEX_EVENTS = [
    {"type": "thread.started", "thread_id": "t-1"},
    {"type": "turn.started"},
    {"type": "item.completed", "item": {"id": "item_0", "type": "error", "message": "unknown config key"}},
    {"type": "turn.completed", "usage": {"input_tokens": 1200, "cached_input_tokens": 1000, "output_tokens": 30}},
    {"type": "turn.started"},
    {"type": "item.completed", "item": {"id": "item_1", "type": "agent_message", "text": REVIEW_TEXT}},
    {"type": "turn.completed", "usage": {"input_tokens": 1500, "cached_input_tokens": 1400, "output_tokens": 70}},
]
CODEX_TOKENS = 1200 + 30 + 1500 + 70

# `claude -p --output-format json`: one JSON object on stdout.
CLAUDE_OUTPUT = {"type": "result", "subtype": "success", "is_error": False, "result": REVIEW_TEXT,
                 "session_id": "s-1", "usage": {"input_tokens": 12, "cache_creation_input_tokens": 3000,
                                                 "cache_read_input_tokens": 9000, "output_tokens": 400}}
CLAUDE_TOKENS = 12 + 3000 + 9000 + 400

FAKE_CODEX = (f"#!{sys.executable}\nimport json, sys\nfrom pathlib import Path\n"
              "args = sys.argv[1:]\nassert '--json' in args\n"
              f"events = {CODEX_EVENTS!r}\n"
              "Path(args[args.index('-o') + 1]).write_text(events[-2]['item']['text'])\n"
              "for event in events:\n    print(json.dumps(event))\n")
FAKE_CLAUDE = (f"#!{sys.executable}\nimport json, sys\n"
               "args = sys.argv[1:]\nassert args[args.index('--output-format') + 1] == 'json'\n"
               f"print(json.dumps({CLAUDE_OUTPUT!r}))\n")


class ExternalReviewTokenTests(SaeTestCase):
    def review_dispatched(self, orchestrator: str) -> tuple[Sandbox, str, str, dict]:
        """A task run by `orchestrator` whose REVIEW-ONE runs in the other harness; returns its COMMAND
        and a shell env with the fake harnesses on PATH."""
        folder = self.tmp / orchestrator
        folder.mkdir()
        sb = Sandbox(folder, points=["all-jobs"], provider="cross-harness")
        sb.env["SAE_HARNESS"] = orchestrator
        task = sb.new_task("tokens", "tokens")
        sb.sae("job", "add", "tokens", "ONE", "--kind", "implementation")
        sb.job_file(task, "ONE")
        sb.approve_plan("tokens")
        sb.sae("start", "tokens")
        ws = dispatch_workspace(sb, task, "ONE")
        sb.work(ws, "one.txt", "1\n", "ONE: work")
        sb.result(task, "jobs/ONE.result.md", status="done", summary="s", validation="pass", changes="made")
        sb.sae("collect", "tokens", "ONE")
        command = sb.json("dispatch", "tokens", "REVIEW-ONE")["command"]
        fake_bin = folder / "fake-bin"
        fake_bin.mkdir()
        for name, script in (("codex", FAKE_CODEX), ("claude", FAKE_CLAUDE)):
            (fake_bin / name).write_text(script)
            (fake_bin / name).chmod(0o755)
        env = dict(sb.env, PATH=str(fake_bin) + os.pathsep + sb.env["PATH"])
        return sb, task, command, env

    def run_command(self, sb: Sandbox, command: str, env: dict) -> None:
        proc = subprocess.run(command, shell=True, cwd=sb.repo, env=env, capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)

    def collected_attempt(self, sb: Sandbox, task: str) -> dict:
        out = sb.sae("collect", "tokens", "REVIEW-ONE").stdout
        self.assertIn("REVIEW-ONE: done — verdict: pass", out)
        return sb.state(task)["jobs"]["REVIEW-ONE"]["attempts"][-1]

    def test_codex_review_records_tokens_summed_over_turns(self):
        sb, task, command, env = self.review_dispatched("claude")
        self.run_command(sb, command, env)
        reviews = sb.task_dir(task) / "reviews"
        self.assertEqual((reviews / "REVIEW-ONE.md").read_text(), REVIEW_TEXT)
        self.assertTrue((reviews / "REVIEW-ONE.codex.jsonl").exists())
        attempt = self.collected_attempt(sb, task)
        self.assertEqual((attempt["harness"], attempt["tokens"]), ("codex", CODEX_TOKENS))
        self.assertFalse((reviews / "REVIEW-ONE.codex.jsonl").exists())
        event = [e for e in sb.events(task) if e["type"] == "job.collected"][-1]
        self.assertEqual(event["tokens"], CODEX_TOKENS)

    def test_claude_review_writes_review_text_and_records_tokens(self):
        sb, task, command, env = self.review_dispatched("codex")
        self.run_command(sb, command, env)
        reviews = sb.task_dir(task) / "reviews"
        self.assertEqual((reviews / "REVIEW-ONE.md").read_text(), REVIEW_TEXT)
        self.assertEqual(json.loads((reviews / "REVIEW-ONE.claude.json").read_text())["result"], REVIEW_TEXT)
        attempt = self.collected_attempt(sb, task)
        self.assertEqual((attempt["harness"], attempt["tokens"]), ("claude", CLAUDE_TOKENS))
        self.assertFalse((reviews / "REVIEW-ONE.claude.json").exists())

    def test_review_without_captured_output_is_collected_without_tokens(self):
        for orchestrator, output in (("claude", "REVIEW-ONE.codex.jsonl"), ("codex", "REVIEW-ONE.claude.json")):
            with self.subTest(orchestrator=orchestrator):
                sb, task, _, _ = self.review_dispatched(orchestrator)
                reviews = sb.task_dir(task) / "reviews"
                reviews.mkdir(exist_ok=True)
                (reviews / "REVIEW-ONE.md").write_text(REVIEW_TEXT)
                if orchestrator == "codex":  # unreadable output counts as missing
                    (reviews / output).write_text("not json\n")
                self.assertIsNone(self.collected_attempt(sb, task)["tokens"])
                self.assertFalse((reviews / output).exists())

    def test_unreadable_output_is_collected_without_tokens(self):
        # invalid UTF-8 and a permission error count as unavailable usage, not as a failed collect
        cases = [("bad-utf8", "claude", "REVIEW-ONE.codex.jsonl")]
        if os.geteuid() != 0:  # root reads a mode-000 file
            cases.append(("no-permission", "codex", "REVIEW-ONE.claude.json"))
        for name, orchestrator, output in cases:
            with self.subTest(name):
                sb, task, _, _ = self.review_dispatched(orchestrator)
                reviews = sb.task_dir(task) / "reviews"
                reviews.mkdir(exist_ok=True)
                (reviews / "REVIEW-ONE.md").write_text(REVIEW_TEXT)
                capture = reviews / output
                if name == "bad-utf8":
                    capture.write_bytes(b'{"type": "turn.completed", "usage": {"input_tokens": 5}}\n\xff\xfe\n')
                else:
                    capture.write_text(json.dumps(CLAUDE_OUTPUT))
                    capture.chmod(0)
                try:
                    self.assertIsNone(self.collected_attempt(sb, task)["tokens"])
                finally:
                    if capture.exists():  # let the sandbox be removed
                        capture.chmod(0o644)

    def test_collect_deletes_no_output_outside_the_record(self):
        """[RECORD-PRIVACY]: a symlinked reviews/ folder leads out of the record; its files stay."""
        sb, task, _, _ = self.review_dispatched("claude")
        reviews = sb.task_dir(task) / "reviews"
        if reviews.exists():
            shutil.rmtree(reviews)
        outside = sb.tmp / "outside"
        outside.mkdir()
        reviews.symlink_to(outside)
        (outside / "REVIEW-ONE.md").write_text(REVIEW_TEXT)
        (outside / "REVIEW-ONE.codex.jsonl").write_text(json.dumps(CODEX_EVENTS[3]) + "\n")
        self.collected_attempt(sb, task)
        self.assertTrue((outside / "REVIEW-ONE.codex.jsonl").exists())

    def test_tokens_given_at_collect_win(self):
        sb, task, command, env = self.review_dispatched("claude")
        self.run_command(sb, command, env)
        sb.sae("collect", "tokens", "REVIEW-ONE", "--tokens", "77")
        self.assertEqual(sb.state(task)["jobs"]["REVIEW-ONE"]["attempts"][-1]["tokens"], 77)
        self.assertFalse((sb.task_dir(task) / "reviews" / "REVIEW-ONE.codex.jsonl").exists())


if __name__ == "__main__":
    unittest.main()
