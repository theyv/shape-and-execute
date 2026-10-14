"""Tests of [MAIN-TOKENS] and [OVERVIEW-PHASE-STATS]: main-session snapshots and per-phase stats.

Run from the repository root:  /usr/bin/python3 -m unittest discover -s tests
The session files are small hand-made samples in the shapes Claude Code and Codex write.
Sandbox strips CLAUDE* and CODEX_* variables; each test sets the ones it needs.
"""

from __future__ import annotations

import datetime as dt
import json
import os
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from saetest import SCRIPTS, Sandbox, SaeTestCase, dispatch_workspace  # noqa: E402

sys.path.insert(0, str(SCRIPTS))
from sae_lib import session_tokens  # noqa: E402

CLAUDE_SESSION = "0d2c4b7e-1111-4a2b-9c3d-aaaaaaaaaaaa"
CODEX_THREAD = "01a13598-2222-7b51-a511-bbbbbbbbbbbb"


def claude_entry(message_id: str, inp: int, out: int, cache_new: int = 0, cache_read: int = 0,
                 sidechain: bool = False) -> dict:
    return {"type": "assistant", "isSidechain": sidechain, "sessionId": CLAUDE_SESSION,
            "message": {"id": message_id, "role": "assistant", "content": [{"type": "text", "text": "…"}],
                        "usage": {"input_tokens": inp, "cache_creation_input_tokens": cache_new,
                                  "cache_read_input_tokens": cache_read, "output_tokens": out,
                                  "service_tier": "standard"}}}


# One response written as two entries with the same id (counts once), a sidechain entry
# (a subagent's; never counted), a user line that mentions "usage", and a half-written last line.
CLAUDE_SAMPLE = [
    {"type": "user", "message": {"role": "user", "content": "what is the usage?"}},
    claude_entry("msg_1", 10, 5, cache_new=100, cache_read=1000),
    claude_entry("msg_1", 10, 5, cache_new=100, cache_read=1000),
    claude_entry("msg_2", 3, 20, cache_read=1200),
    claude_entry("msg_sub", 999, 999, sidechain=True),
    {"type": "system", "subtype": "info"},
]
CLAUDE_SAMPLE_TOTAL = (10 + 5 + 100 + 1000) + (3 + 20 + 1200)


def token_count(total: int | None) -> dict:
    info = None if total is None else {
        "total_token_usage": {"input_tokens": total - 10, "cached_input_tokens": total // 2,
                              "cache_write_input_tokens": 0, "output_tokens": 10,
                              "reasoning_output_tokens": 0, "total_tokens": total},
        "last_token_usage": {"total_tokens": 1}, "model_context_window": 1000}
    return {"timestamp": "2026-10-13T15:44:24.000Z", "type": "event_msg",
            "payload": {"type": "token_count", "info": info, "rate_limits": {}}}


# The last token_count with an `info` wins; a later rate-limits-only one (info null) carries no total.
CODEX_SAMPLE = [
    {"type": "session_meta", "payload": {"id": CODEX_THREAD, "cli_version": "0.162.1"}},
    token_count(1500),
    {"type": "response_item", "payload": {"type": "message", "content": "token_count is a word here"}},
    token_count(4200),
    token_count(None),
    {"type": "event_msg", "payload": {"type": "agent_message", "message": "done"}},
]
CODEX_SAMPLE_TOTAL = 4200


def write_jsonl(path: Path, entries: list[dict], tail: str = "") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(e) + "\n" for e in entries) + tail)
    return path


class SessionFiles:
    """A Claude config dir and a Codex home with one session each, and the env that points to them."""

    def __init__(self, tmp: Path):
        self.claude_dir = tmp / "claude-config"
        self.codex_home = tmp / "codex-home"
        self.transcript = self.claude_dir / "projects" / "-tmp-repo" / f"{CLAUDE_SESSION}.jsonl"
        self.rollout = (self.codex_home / "sessions" / "2026" / "10" / "13"
                        / f"rollout-2026-10-13T15-44-24-{CODEX_THREAD}.jsonl")
        self.claude_total = 0
        self.codex_total = 0
        self.claude_n = 0
        write_jsonl(self.transcript, [])
        write_jsonl(self.rollout, [CODEX_SAMPLE[0]])

    def claude_env(self) -> dict:
        return {"SAE_HARNESS": "claude", "CLAUDECODE": "1", "CLAUDE_CODE_SESSION_ID": CLAUDE_SESSION,
                "CLAUDE_CONFIG_DIR": str(self.claude_dir)}

    def codex_env(self) -> dict:
        return {"SAE_HARNESS": "codex", "CODEX_THREAD_ID": CODEX_THREAD, "CODEX_HOME": str(self.codex_home)}

    def claude_spends(self, tokens: int) -> int:
        """Appends one response (as two entries with one id) of `tokens` tokens; returns the total."""
        self.claude_n += 1
        entry = claude_entry(f"msg_{self.claude_n}", tokens - 1, 1)
        with self.transcript.open("a") as handle:
            handle.write(json.dumps(entry) + "\n" + json.dumps(entry) + "\n")
        self.claude_total += tokens
        return self.claude_total

    def codex_spends(self, tokens: int) -> int:
        self.codex_total += tokens
        with self.rollout.open("a") as handle:
            handle.write(json.dumps(token_count(self.codex_total)) + "\n")
        return self.codex_total


def use_session(sb: Sandbox, env: dict) -> None:
    for name in ("CLAUDECODE", "CLAUDE_CODE_SESSION_ID", "CLAUDE_CONFIG_DIR", "CODEX_THREAD_ID"):
        sb.env.pop(name, None)
    sb.env.update(env)


def snapshots(sb: Sandbox, task: str) -> list[dict]:
    return [e for e in sb.events(task) if e["type"] == "session.snapshot"]


class SessionFileReaderTests(unittest.TestCase):
    def setUp(self):
        import tempfile
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_claude_transcript_counts_unique_messages_without_sidechain(self):
        path = write_jsonl(self.tmp / "t.jsonl", CLAUDE_SAMPLE, tail='{"type": "assistant", "message": {"usa')
        self.assertEqual(session_tokens.claude_total(path), CLAUDE_SAMPLE_TOTAL)

    def test_claude_unknown_shape_gives_no_total(self):
        broken = claude_entry("msg_9", 1, 1)
        broken["message"]["usage"]["output_tokens"] = "many"
        self.assertIsNone(session_tokens.claude_total(write_jsonl(self.tmp / "a.jsonl", CLAUDE_SAMPLE + [broken])))
        no_id = claude_entry("msg_9", 1, 1)
        del no_id["message"]["id"]
        self.assertIsNone(session_tokens.claude_total(write_jsonl(self.tmp / "b.jsonl", [no_id])))
        self.assertIsNone(session_tokens.claude_total(write_jsonl(self.tmp / "c.jsonl", CLAUDE_SAMPLE[:1])))

    def test_claude_missing_usage_or_bad_line_gives_no_partial_total(self):
        valid = claude_entry("msg_1", 10, 5)  # 15 tokens
        no_usage = claude_entry("msg_2", 1, 1)
        del no_usage["message"]["usage"]
        not_a_message = {"type": "assistant", "message": "text"}
        for name, entries, tail in (("no-usage", [valid, no_usage], ""), ("no-message", [valid, not_a_message], ""),
                                    ("bad-last-line-complete", [valid], '{"type": "assist\n')):
            path = write_jsonl(self.tmp / f"{name}.jsonl", entries, tail=tail)
            self.assertIsNone(session_tokens.claude_total(path), name)
        bad_interior = self.tmp / "bad-interior.jsonl"
        bad_interior.write_text(json.dumps(valid) + "\n" + '{"type": "assist' + "\n" + json.dumps(claude_entry("msg_3", 1, 1)) + "\n")
        self.assertIsNone(session_tokens.claude_total(bad_interior))
        # a sidechain entry without usage is not the main session's; a half-written last line is tolerated
        side = dict(no_usage, isSidechain=True)
        path = write_jsonl(self.tmp / "ok.jsonl", [valid, side], tail='{"type": "assistant", "mess')
        self.assertEqual(session_tokens.claude_total(path), 15)

    def test_codex_rollout_last_token_count(self):
        path = write_jsonl(self.tmp / "r.jsonl", CODEX_SAMPLE)
        self.assertEqual(session_tokens.codex_total(path), CODEX_SAMPLE_TOTAL)
        # a rollout larger than one read block, the last total far from the end of the file
        padding = {"type": "response_item", "payload": {"type": "message", "content": "x" * 1000}}
        big = write_jsonl(self.tmp / "big.jsonl", CODEX_SAMPLE[:2] + [token_count(7777)] + [padding] * 2500)
        self.assertGreater(big.stat().st_size, session_tokens.TAIL_BLOCK * 2)
        self.assertEqual(session_tokens.codex_total(big), 7777)
        self.assertIsNone(session_tokens.codex_total(write_jsonl(self.tmp / "none.jsonl", CODEX_SAMPLE[:1])))

    def test_session_total_finds_the_file_by_session_id(self):
        files = SessionFiles(self.tmp)
        write_jsonl(files.transcript, CLAUDE_SAMPLE)
        write_jsonl(files.rollout, CODEX_SAMPLE)
        self.assertEqual(session_tokens.session_total(files.claude_env()),
                         {"harness": "claude", "session": CLAUDE_SESSION, "total": CLAUDE_SAMPLE_TOTAL})
        self.assertEqual(session_tokens.session_total(files.codex_env()),
                         {"harness": "codex", "session": CODEX_THREAD, "total": CODEX_SAMPLE_TOTAL})
        for env in ({}, {**files.claude_env(), "CLAUDE_CODE_SESSION_ID": "*"},
                    {**files.codex_env(), "CODEX_THREAD_ID": "other"}, {"SAE_HARNESS": "codex"}):
            self.assertIsNone(session_tokens.session_total(env), env)


class SnapshotCommandTests(SaeTestCase):
    def test_unreadable_session_file_records_nothing_and_the_command_succeeds(self):
        sb = self.sandbox()
        files = SessionFiles(self.tmp)
        use_session(sb, files.claude_env())
        files.transcript.write_text('{"type": "assistant", "message": {"id": "m", "usage": [1, 2]}}\n')
        task = sb.new_task("garbled", "garbled")  # an unknown shape
        self.assertEqual(snapshots(sb, task), [])
        files.claude_spends(500)
        files.transcript.chmod(0)
        try:
            if os.access(files.transcript, os.R_OK):
                self.skipTest("running as a user who reads any file")
            sb.approve_spec("garbled")
        finally:
            files.transcript.chmod(0o600)
        self.assertEqual(snapshots(sb, task), [])
        files.transcript.unlink()  # a missing file
        sb.sae("job", "add", "garbled", "ONE", "--kind", "implementation")
        sb.job_file(task, "ONE")
        sb.sae("approve", "garbled", "plan")
        self.assertEqual(snapshots(sb, task), [])
        self.assertEqual(sb.state(task)["task"]["phase"], "planning")

    def test_two_sessions_give_per_phase_numbers(self):
        sb = self.sandbox()
        files = SessionFiles(self.tmp)
        # Session A (Claude Code): shaping and planning.
        use_session(sb, files.claude_env())
        files.claude_spends(1000)
        task = sb.new_task("two sessions", "two")
        files.claude_spends(2500)
        sb.approve_spec("two")
        sb.sae("job", "add", "two", "ONE", "--kind", "implementation")
        sb.job_file(task, "ONE")
        files.claude_spends(4000)
        sb.sae("approve", "two", "plan")
        files.claude_spends(777)  # after A's last snapshot: a known gap, counted nowhere
        # Session B (Codex): execution.
        use_session(sb, files.codex_env())
        files.codex_spends(9000)  # before B's first snapshot: not attributable
        sb.sae("start", "two")
        files.codex_spends(300)
        ws = dispatch_workspace(sb, task, "ONE")
        before = sb.events(task)
        sb.sae("next", "two")
        sb.sae("status", "two")
        self.assertEqual(sb.events(task), before)  # read-only commands take no snapshot ([AMEND-1])
        files.codex_spends(1200)
        sb.work(ws, "one.txt", "1\n", "ONE: work")
        sb.result(task, "jobs/ONE.result.md", status="done", summary="s", validation="pass", changes="made")
        sb.sae("collect", "two", "ONE", "--tokens", "50000", "--duration-s", "90")
        files.codex_spends(400)
        sb.sae("finish", "two")

        snaps = snapshots(sb, task)
        self.assertEqual([(s["command"], s["harness"], s["phase_before"], s["phase"]) for s in snaps], [
            ("new", "claude", None, "shaping"), ("approve spec", "claude", "shaping", "planning"),
            ("approve plan", "claude", "planning", "planning"), ("start", "codex", "planning", "executing"),
            ("dispatch", "codex", "executing", "executing"), ("collect", "codex", "executing", "executing"),
            ("finish", "codex", "executing", "done")])
        self.assertEqual([s["total"] for s in snaps], [1000, 3500, 7500, 9000, 9300, 10500, 10900])

        rows = {r["phase"]: r for r in session_tokens.phase_stats(sb.state(task), sb.events(task))}
        self.assertEqual(list(rows), ["shape", "plan", "execution"])
        self.assertEqual((rows["shape"]["main_tokens"], rows["plan"]["main_tokens"],
                          rows["execution"]["main_tokens"]), (2500, 4000, 300 + 1200 + 400))
        execution = rows["execution"]
        self.assertEqual((execution["subagent_tokens"], execution["tokens"], execution["subagent_s"],
                          execution["jobs"], execution["attempts"]), (50000, 51900, 90, 1, 1))
        self.assertEqual((rows["shape"]["tokens"], rows["shape"]["attempts"]), (2500, 0))
        for row in rows.values():
            self.assertIsNone(row["main_note"])
            self.assertFalse(row["running"])
            self.assertIsNotNone(row["ended"])
            self.assertGreaterEqual(row["wall_s"], 0)


class PhaseStatsTests(unittest.TestCase):
    """phase_stats on hand-made records: old tasks, a running phase, a phase change in another session."""

    T0 = dt.datetime(2026, 10, 13, 10, 0, tzinfo=dt.timezone.utc)

    def at(self, minutes: int) -> str:
        return (self.T0 + dt.timedelta(minutes=minutes)).isoformat()

    def snap(self, minutes, session, total, before, phase) -> dict:
        return {"at": self.at(minutes), "type": "session.snapshot", "command": "x", "phase_before": before,
                "phase": phase, "harness": "claude", "session": session, "total": total}

    def test_old_task_without_snapshots(self):
        state = {"task": {"phase": "done"}, "jobs": {
            "SPEC-REVIEW": {"kind": "review", "target": "spec", "attempts": [
                {"started": self.at(5), "tokens": 700, "duration_s": 30}]},
            "ONE": {"kind": "implementation", "attempts": [
                {"started": self.at(70), "tokens": 1000, "duration_s": 60},
                {"started": self.at(80), "tokens": None, "duration_s": None}]}}}
        events = [{"at": self.at(0), "type": "task.created"}, {"at": self.at(30), "type": "spec.approved"},
                  {"at": self.at(50), "type": "plan.approved"},
                  {"at": self.at(60), "type": "execution.started", "resumed": False},
                  {"at": self.at(65), "type": "execution.started", "resumed": True},
                  {"at": self.at(120), "type": "task.finished"}]
        rows = {r["phase"]: r for r in session_tokens.phase_stats(state, events)}
        self.assertEqual([rows[p]["wall_s"] for p in ("shape", "plan", "execution")], [1800, 1800, 3600])
        self.assertEqual((rows["shape"]["subagent_tokens"], rows["shape"]["jobs"]), (700, 1))
        self.assertEqual((rows["execution"]["subagent_tokens"], rows["execution"]["attempts"],
                          rows["execution"]["jobs"], rows["execution"]["subagent_s"]), (1000, 2, 1, 60))
        for row in rows.values():
            self.assertIsNone(row["main_tokens"])
            self.assertIsNone(row["tokens"])
            self.assertEqual(row["main_note"], session_tokens.NOTE_NO_SNAPSHOT)

    def test_running_phase_and_phase_change_in_another_session(self):
        state = {"task": {"phase": "executing"}, "jobs": {}}
        events = [{"at": self.at(0), "type": "task.created"}, self.snap(0, "A", 100, None, "shaping"),
                  {"at": self.at(30), "type": "spec.approved"},
                  self.snap(30, "B", 5000, "shaping", "planning"),  # B's first snapshot
                  {"at": self.at(40), "type": "execution.started", "resumed": False},
                  self.snap(40, "B", 5600, "planning", "executing"),
                  self.snap(50, "A", 900, "executing", "executing")]  # A's pair spans B's phase changes
        rows = {r["phase"]: r for r in session_tokens.phase_stats(state, events, now=self.T0 + dt.timedelta(minutes=55))}
        self.assertEqual((rows["shape"]["main_tokens"], rows["shape"]["main_note"]),
                         (None, session_tokens.NOTE_OTHER_SESSION))
        self.assertEqual(rows["plan"]["main_tokens"], 600)
        self.assertEqual((rows["execution"]["main_tokens"], rows["execution"]["main_note"]),
                         (None, session_tokens.NOTE_ONE_SNAPSHOT))
        self.assertTrue(rows["execution"]["running"])
        self.assertEqual((rows["execution"]["wall_s"], rows["execution"]["ended"]), (15 * 60, None))

    def test_phase_not_started(self):
        rows = session_tokens.phase_stats({"task": {"phase": "shaping"}, "jobs": {}},
                                          [{"at": self.at(0), "type": "task.created"}],
                                          now=self.T0 + dt.timedelta(minutes=5))
        self.assertEqual([(r["phase"], r["wall_s"], r["running"]) for r in rows],
                         [("shape", 300, True), ("plan", None, False), ("execution", None, False)])
        self.assertEqual(rows[1]["main_note"], session_tokens.NOTE_NOT_STARTED)

    def test_old_task_without_execution_started_attributes_by_kind_or_not_at_all(self):
        state = {"task": {"phase": "done"}, "jobs": {
            "SPEC-REVIEW": {"kind": "review", "target": "spec", "attempts": [{"started": self.at(5), "tokens": 700}]},
            "PLAN-REVIEW": {"kind": "review", "target": "plan", "attempts": [{"started": self.at(40), "tokens": 300}]},
            "ONE": {"kind": "implementation", "attempts": [{"started": self.at(70), "tokens": 900, "duration_s": 60}]},
            "LOOK": {"kind": "research", "attempts": [{"started": self.at(75), "tokens": 50}]},
            "REVIEW-ONE": {"kind": "review", "target": "ONE", "attempts": [{"started": self.at(80), "tokens": 20}]}}}
        events = [{"at": self.at(0), "type": "task.created"}, {"at": self.at(30), "type": "spec.approved"},
                  {"at": self.at(50), "type": "plan.approved"}, {"at": self.at(120), "type": "task.finished"}]
        rows = {r["phase"]: r for r in session_tokens.phase_stats(state, events)}
        self.assertEqual((rows["shape"]["subagent_tokens"], rows["shape"]["subagent_note"]), (700, None))
        # before plan approval nothing runs in execution; implementation and job reviews run only there
        self.assertEqual(rows["plan"]["subagent_tokens"], 300)
        self.assertEqual((rows["execution"]["subagent_tokens"], rows["execution"]["jobs"]), (920, 2))
        # research after plan approval may be in Plan or Execution: counted in neither
        note = session_tokens.NOTE_UNATTRIBUTED.format(n=1)
        self.assertEqual((rows["plan"]["subagent_note"], rows["execution"]["subagent_note"]), (note, note))

    def test_same_second_phase_change_resolves_by_event_order(self):
        same = self.at(30)
        state = {"task": {"phase": "planning"}, "jobs": {
            "REVIEW-SPEC": {"kind": "review", "target": "spec", "attempts": [{"n": 1, "started": same, "tokens": 700}]},
            "LOOK": {"kind": "research", "attempts": [{"n": 1, "started": same, "tokens": 40}]}}}
        events = [{"at": self.at(0), "type": "task.created"},
                  {"at": same, "type": "job.dispatched", "job": "REVIEW-SPEC", "attempt": 1},
                  {"at": same, "type": "job.collected", "job": "REVIEW-SPEC", "attempt": 1},
                  {"at": same, "type": "spec.approved"},
                  {"at": same, "type": "job.dispatched", "job": "LOOK", "attempt": 1}]
        rows = {r["phase"]: r for r in session_tokens.phase_stats(state, events, now=self.T0 + dt.timedelta(minutes=40))}
        self.assertEqual((rows["shape"]["subagent_tokens"], rows["plan"]["subagent_tokens"]), (700, 40))
        # without the dispatch event an equal time is not a guess: research may be in either phase
        events = [e for e in events if e.get("job") != "LOOK"]
        rows = {r["phase"]: r for r in session_tokens.phase_stats(state, events, now=self.T0 + dt.timedelta(minutes=40))}
        self.assertEqual((rows["shape"]["subagent_tokens"], rows["plan"]["subagent_tokens"]), (700, 0))
        self.assertEqual(rows["plan"]["subagent_note"], session_tokens.NOTE_UNATTRIBUTED.format(n=1))


if __name__ == "__main__":
    unittest.main()
