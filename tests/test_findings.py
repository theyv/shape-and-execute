"""Findings with bodies, decision-record drafts, triage counts and YAML escapes."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from saetest import SCRIPTS, SKILL_DIR, SaeTestCase

sys.path.insert(0, str(SCRIPTS))
from sae_lib.markdown import split_frontmatter  # noqa: E402


class FindingBodyTests(SaeTestCase):
    def test_finding_without_body_is_refused_with_the_form(self):
        sb = self.sandbox()
        proc = sb.sae("finding", "new", "Slow", "--type", "defect", "--confidence", "low", code=1)
        self.assertIn("--body", proc.stderr)
        self.assertIn("Expected form", proc.stderr)
        sb.sae("finding", "new", "Slow", "--type", "defect", "--confidence", "low", "--body", "  ", code=1)
        self.assertFalse((sb.repo / ".tasks" / "findings").exists())

    def test_long_title_is_refused_with_a_hint(self):
        sb = self.sandbox()
        proc = sb.sae("finding", "new", "x" * 81, "--type", "defect", "--confidence", "low", "--body", "b", code=1)
        self.assertIn("move the text into --body", " ".join(proc.stderr.split()))

    def test_body_lands_under_observation(self):
        sb = self.sandbox()
        path = Path(sb.json("finding", "new", "Slow", "--type", "friction", "--confidence", "high",
                            "--body", "Lookup takes 4 s.")["file"])
        body = split_frontmatter(path.read_text())[1]
        self.assertIn("## Observation\nLookup takes 4 s.\n", body)
        note = self.tmp / "note.md"
        note.write_text("From a file.\n")
        path = Path(sb.json("finding", "new", "Other", "--type", "follow-up", "--confidence", "low",
                            "--body-file", str(note))["file"])
        self.assertIn("From a file.", path.read_text())


class DecisionDraftTests(SaeTestCase):
    def test_template_has_the_record_fields(self):
        front, body = split_frontmatter((SKILL_DIR / "templates" / "decision-record.md").read_text())
        self.assertEqual(set(front), {"title", "type", "status", "date", "source", "applies-to"})
        self.assertEqual(front["status"], "proposed")
        for section in ("Context", "Decision", "Why", "Rejected options", "Consequences"):
            self.assertIn(f"## {section}\n", body)

    def new_draft(self, sb, title="Cache status for 60 s") -> Path:
        sb.new_task("drafts", "drafts")
        return Path(sb.json("adr", "new", "drafts", title, "--type", "business",
                            "--applies-to", "src/status,StatusCache")["file"])

    def test_adr_new_writes_a_proposed_draft(self):
        sb = self.sandbox()
        path = self.new_draft(sb)
        self.assertEqual(path.parent, sb.repo / ".tasks" / "adr")
        self.assertRegex(path.name, r"^\d{4}-\d{2}-\d{2}-cache-status-for-60-s\.md$")
        front, body = split_frontmatter(path.read_text())
        self.assertEqual(front["status"], "proposed")
        self.assertEqual(front["type"], "business")
        self.assertEqual(front["applies-to"], ["src/status", "StatusCache"])
        self.assertTrue(front["source"].endswith("--drafts"))
        self.assertIn("# Cache status for 60 s", body)
        task = front["source"]
        self.assertTrue(any(e["type"] == "adr.created" for e in sb.events(task)))
        again = Path(sb.json("adr", "new", "drafts", "Cache status for 60 s", "--type", "business")["file"])
        self.assertTrue(again.name.endswith("-2.md"))

    def test_accept_goes_to_default_then_existing_then_pinned_folder(self):
        sb = self.sandbox()
        path = self.new_draft(sb)
        data = sb.json("adr", "accept", path.name)
        target = sb.repo / "docs" / "decisions" / path.name
        self.assertEqual(Path(data["file"]), target)
        self.assertTrue(data["first"])
        self.assertIn("status: accepted", target.read_text())
        self.assertFalse(path.exists())
        self.assertIn("docs/", sb.git("status", "--porcelain"))  # uncommitted
        # an existing ADR folder wins over the default
        (sb.repo / "docs" / "decisions" / path.name).unlink()
        (sb.repo / "docs" / "decisions").rmdir()
        (sb.repo / "doc" / "adr").mkdir(parents=True)
        second = Path(sb.json("adr", "new", "drafts", "Second", "--type", "architecture")["file"])
        self.assertEqual(Path(sb.json("adr", "accept", str(second))["file"]).parent, sb.repo / "doc" / "adr")
        # a pin in the repo profile wins over everything
        (sb.repo / ".tasks" / "repo").mkdir()
        (sb.repo / ".tasks" / "repo" / "profile.md").write_text("---\nadr_folder: records/adr\n---\n")
        third = Path(sb.json("adr", "new", "drafts", "Third", "--type", "architecture")["file"])
        data = sb.json("adr", "accept", str(third))
        self.assertEqual(Path(data["file"]).parent, sb.repo / "records" / "adr")
        fourth = Path(sb.json("adr", "new", "drafts", "Fourth", "--type", "architecture")["file"])
        self.assertFalse(sb.json("adr", "accept", str(fourth))["first"])

    def test_reject_closes_with_reason(self):
        sb = self.sandbox()
        path = self.new_draft(sb)
        sb.sae("adr", "reject", path.name, code=1)
        sb.sae("adr", "reject", path.name, "--reason", "visible in the code")
        self.assertFalse(path.exists())
        closed = (sb.repo / ".tasks" / "adr" / "closed.md").read_text()
        self.assertIn(f"{path.stem} · Cache status for 60 s · rejected: visible in the code", closed)
        self.assertIn("adr/closed.md merge=union", (sb.repo / ".tasks" / ".gitattributes").read_text())

    def test_rejected_live_draft_is_committed_with_task_and_omitted_from_report(self):
        sb = self.sandbox()
        task = sb.new_task("Live decision drafts", "live-drafts")
        sb.sae("job", "add", task, "CHECK", "--kind", "validation")
        sb.job_file(task, "CHECK")
        sb.approve_plan(task)
        sb.sae("start", task)
        rejected = Path(sb.json("adr", "new", task, "Reject this draft", "--type", "business")["file"])
        kept = Path(sb.json("adr", "new", task, "Keep this draft", "--type", "architecture")["file"])
        sb.sae("adr", "reject", str(rejected), "--reason", "Already clear from the code.")
        worktree = sb.task_worktree(task)
        closed = worktree / ".tasks" / "adr" / "closed.md"
        self.assertTrue(closed.is_file())
        self.assertIn(rejected.stem, closed.read_text())
        self.assertIn("adr/closed.md merge=union", (worktree / ".tasks" / ".gitattributes").read_text())
        self.assertFalse((sb.repo / ".tasks" / "adr" / "closed.md").exists())
        report = sb.json("finish", task, "--with-open")["report"]
        self.assertNotIn(rejected.name, report)
        self.assertIn(kept.name, report)
        self.assertIn(rejected.stem, sb.git("show", "HEAD:.tasks/adr/closed.md", cwd=worktree))
        self.assertIn("adr/closed.md merge=union", sb.git("show", "HEAD:.tasks/.gitattributes", cwd=worktree))

    def test_help(self):
        sb = self.sandbox()
        for args in (["adr", "new"], ["adr", "accept"], ["adr", "reject"], ["triage"]):
            out = sb.sae(*args, "--help").stdout
            self.assertIn("Exit codes:", out, args)
            self.assertIn("Examples:", out, args)


class TriageTests(SaeTestCase):
    def test_counts_table(self):
        sb = self.sandbox()
        out = sb.sae("triage").stdout
        self.assertIn("Queue", out)
        self.assertRegex(out, r"decision drafts\s+0\s+-")
        findings = sb.repo / ".tasks" / "findings"
        findings.mkdir(parents=True)
        (findings / "2020-01-01-1000--old.md").write_text("---\ntype: defect\n---\n\n# Old\n")
        (findings / "2020-01-05-1000--newer.md").write_text("---\ntype: defect\n---\n\n# Newer\n")
        (findings / "closed.md").write_text("# Closed findings\n")
        sb.new_task("t", "t")
        sb.sae("adr", "new", "t", "Draft", "--type", "business")
        data = {r["queue"]: r for r in sb.json("triage")["queues"]}
        self.assertEqual(data["defect"]["open"], 2)
        self.assertEqual(data["defect"]["oldest"], "2020-01-01")
        self.assertEqual(data["friction"]["open"], 0)
        self.assertEqual(data["decision drafts"]["open"], 1)
        self.assertEqual(data["decision drafts"]["age"], "0 days")
        self.assertRegex(sb.sae("triage").stdout, r"defect\s+2\s+\d+ days")


class YamlEscapeTests(SaeTestCase):
    def parse(self, line: str):
        return split_frontmatter(f"---\n{line}\n---\n")[0]["v"]

    def test_double_and_single_quotes(self):
        self.assertEqual(self.parse(r'v: "a \\ b \" c\nd\te"'), 'a \\ b " c\nd\te')
        self.assertEqual(self.parse("v: 'it''s'"), "it's")
        self.assertEqual(self.parse(r'''v: ["x \" # y", 'a''b'] # comment'''), ['x " # y', "a'b"])
        self.assertEqual(self.parse('v: "plain # kept"  # dropped'), "plain # kept")
        self.assertEqual(self.parse("v: plain value"), "plain value")
        self.assertEqual(self.parse(r'v: "C:\path"'), r"C:\path")  # unknown escape stays

    def test_pilot_project_verify_command_runs_as_intended(self):
        # The pilot-project verify line (FORENSICS §7), with grep in place of rg.
        line = r'''verify: ["! grep -rnE \"'gpt-[0-9][^']*'|'claude-[a-z0-9-]+'\" --include='*.mjs' src"]'''
        command = split_frontmatter(f"---\n{line}\n---\n")[0]["verify"][0]
        self.assertEqual(command, "! grep -rnE \"'gpt-[0-9][^']*'|'claude-[a-z0-9-]+'\" --include='*.mjs' src")
        src = self.tmp / "src"
        src.mkdir()
        (src / "a.mjs").write_text("const model = config.model;\n")
        run = lambda: subprocess.run(command, shell=True, cwd=self.tmp, capture_output=True).returncode
        self.assertEqual(run(), 0)
        (src / "b.mjs").write_text("const model = 'gpt-5';\n")
        self.assertEqual(run(), 1)
