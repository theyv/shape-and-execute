"""Pointer lines in `sae dispatch` prompts: [WORKER-POINTERS], [REVIEW-POINTERS], [DIR-POINTERS],
[POINTER-LIMIT] and [INDEX-POINTER].

Run from the repository root:  python3 tests/run.py test_dispatch_pointers
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from saetest import Sandbox, SaeTestCase  # noqa: E402

RECORDS = "Decision records that guard these paths"
DIRS = "Directory instructions for these paths"


def write_record(sb: Sandbox, name: str, applies: str, folder: str = "docs/adr") -> None:
    path = sb.repo / folder / f"{name}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"---\ntitle: Record {name}\nstatus: accepted\napplies-to: [{applies}]\n---\n\n"
                    f"# Record {name}\n\n## Decision\nDecision of {name}. More text.\n")


def write_index(sb: Sandbox, names: list[str], folder: str = "docs/adr") -> None:
    lines = [f"- [Record {n}]({n}.md) — Indexed decision of {n}." for n in names]
    (sb.repo / folder / "index.md").write_text("# Index\n\n" + "\n".join(lines) + "\n")


def write_file(sb: Sandbox, rel: str, text: str = "x\n") -> None:
    path = sb.repo / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def commit(sb: Sandbox) -> None:
    sb.git("add", "-A")
    sb.git("commit", "-q", "-m", "records")


class PointerCase(SaeTestCase):
    def started(self, sb: Sandbox, slug: str, jobs: dict) -> str:
        """A started task with one implementation job per entry of `jobs` (job ID → job_file options)."""
        task = sb.new_task(slug, slug)
        for job_id, options in jobs.items():
            sb.sae("job", "add", slug, job_id, "--kind", "implementation")
            sb.job_file(task, job_id, **options)
        sb.approve_plan(slug)
        sb.sae("start", slug)
        return task

    def prompt(self, sb: Sandbox, slug: str, job: str, *extra: str) -> dict:
        return sb.json("dispatch", slug, job, *extra)


class WorkerPointerTests(PointerCase):
    def test_scope_matches_a_file_record_and_a_folder_record(self):
        sb = self.sandbox()
        write_record(sb, "a-file", "skills/x/assets/viewer/app.css, ViewerApp")
        write_record(sb, "b-folder", "skills/x/assets/")
        write_record(sb, "c-other", "skills/x/scripts/")
        write_index(sb, ["a-file", "b-folder", "c-other"])
        commit(sb)
        self.started(sb, "scoped", {"ONE": {"scope": ["skills/x/assets/viewer/"]}})
        data = self.prompt(sb, "scoped", "ONE")
        lines = data["prompt"].splitlines()
        at = lines.index(RECORDS + " — open the ones your work touches:")
        self.assertEqual(lines[at + 1:at + 3], [
            "- [Record a-file](docs/adr/a-file.md) — Indexed decision of a-file.",
            "- [Record b-folder](docs/adr/b-folder.md) — Indexed decision of b-folder."])
        self.assertNotIn("c-other", data["prompt"])
        self.assertTrue((Path(data["workspace"]) / "docs/adr/a-file.md").is_file())  # the link opens from the workdir

    def test_job_file_names_the_path_without_scope(self):
        sb = self.sandbox()
        write_record(sb, "named", "skills/x/scripts/prompts.py")
        write_record(sb, "unnamed", "skills/x/scripts/other.py")
        commit(sb)  # no index.md: [EDGE-NO-INDEX-LINE]
        self.started(sb, "named", {"ONE": {"objective": "Change `skills/x/scripts/prompts.py`."}})
        prompt = self.prompt(sb, "named", "ONE")["prompt"]
        self.assertIn("\n- [Record named](docs/adr/named.md) — Decision of named.\n", prompt)
        self.assertNotIn("unnamed", prompt)

    def test_glob_scope_matches_the_folders_it_covers(self):
        sb = self.sandbox()
        write_record(sb, "a-lib", "skills/x/scripts/lib/")
        write_record(sb, "b-file", "skills/x/scripts/lib/deep/c.py")
        write_record(sb, "c-text", "skills/x/scripts/notes.txt")
        write_record(sb, "d-assets", "skills/x/assets/")
        write_file(sb, "skills/x/scripts/notes.txt")
        write_file(sb, "skills/x/scripts/lib/deep/c.py")
        write_file(sb, "skills/x/assets/a.py")
        write_index(sb, ["a-lib", "b-file", "c-text", "d-assets"])
        commit(sb)
        self.started(sb, "globs", {"ONE": {"scope": ["skills/x/scripts/**/*.py"]},
                                   "TWO": {"scope": ["skills/x/scripts/*.py"]}})
        prompt = self.prompt(sb, "globs", "ONE")["prompt"]
        self.assertIn("- [Record a-lib](docs/adr/a-lib.md)", prompt)
        self.assertIn("- [Record b-file](docs/adr/b-file.md)", prompt)
        self.assertNotIn("Record c-text", prompt)  # a file the glob does not match
        self.assertNotIn("Record d-assets", prompt)
        self.assertNotIn("Record a-lib", self.prompt(sb, "globs", "TWO")["prompt"])  # `*` stays in one folder

    def test_job_file_names_a_top_level_folder(self):
        sb = self.sandbox()
        write_record(sb, "main", "src/main.py")
        write_record(sb, "other", "lib/main.py")
        write_file(sb, "src/AGENTS.md")
        write_file(sb, "lib/AGENTS.md")
        write_index(sb, ["main", "other"])
        commit(sb)
        self.started(sb, "top", {"ONE": {"objective": "Change `src/`."}})
        prompt = self.prompt(sb, "top", "ONE")["prompt"]
        self.assertIn("- [Record main](docs/adr/main.md)", prompt)
        self.assertIn("\n- src/AGENTS.md\n", prompt)
        self.assertNotIn("Record other", prompt)
        self.assertNotIn("lib/AGENTS.md", prompt)

    def test_code_names_never_match(self):
        sb = self.sandbox()
        write_record(sb, "names", "cmd_set, settings.json, viewer")
        write_index(sb, ["names"])
        commit(sb)
        self.started(sb, "names", {"ONE": {"objective": "Fix cmd_set in settings.json of the viewer."},
                                   "TWO": {"scope": ["viewer/settings.json", "cmd_set"]}})
        self.assertNotIn(RECORDS, self.prompt(sb, "names", "ONE")["prompt"])
        self.assertNotIn(RECORDS, self.prompt(sb, "names", "TWO")["prompt"])

    def test_no_match_and_no_adr_folder_give_the_same_prompt(self):
        sb = self.sandbox()
        write_record(sb, "elsewhere", "skills/x/other/")
        write_index(sb, ["elsewhere"])
        commit(sb)
        self.started(sb, "same", {"ONE": {"scope": ["skills/x/assets/"]}})
        data = self.prompt(sb, "same", "ONE")
        self.assertNotIn(RECORDS, data["prompt"])
        self.assertNotIn(DIRS, data["prompt"])
        ws = Path(data["workspace"])  # records are read from the workdir: remove the ADR folder there
        sb.git("rm", "-rq", "docs", cwd=ws)
        sb.git("commit", "-q", "-m", "ONE: no records", cwd=ws)
        again = self.prompt(sb, "same", "ONE", "--resume", "--reason", "again")["prompt"]
        self.assertTrue(again.endswith("\n" + data["prompt"]), again)


class DirectoryPointerTests(PointerCase):
    def test_directory_files_below_the_root(self):
        sb = self.sandbox()
        write_file(sb, "AGENTS.md", "# root\n")
        write_file(sb, "CLAUDE.md", "# root\n")
        write_file(sb, "skills/x/CLAUDE.md", "# x\n")
        write_file(sb, "skills/x/assets/viewer/AGENTS.md", "# viewer\n")
        write_file(sb, "skills/x/scripts/AGENTS.md", "# scripts\n")
        commit(sb)  # no ADR folder at all
        self.started(sb, "dirs", {"ONE": {"scope": ["skills/x/assets/viewer/app.css"]}})
        lines = self.prompt(sb, "dirs", "ONE")["prompt"].splitlines()
        at = lines.index(DIRS + " — read them:")
        self.assertEqual(lines[at + 1:at + 3], ["- skills/x/CLAUDE.md", "- skills/x/assets/viewer/AGENTS.md"])
        self.assertNotIn("- AGENTS.md", lines)
        self.assertNotIn("- CLAUDE.md", lines)
        self.assertNotIn("- skills/x/scripts/AGENTS.md", lines)
        self.assertNotIn(RECORDS, "\n".join(lines))

    def test_glob_scope_gets_the_files_of_the_folders_it_covers(self):
        sb = self.sandbox()
        write_file(sb, "skills/x/scripts/AGENTS.md")
        write_file(sb, "skills/x/scripts/lib/AGENTS.md")
        write_file(sb, "skills/x/scripts/lib/deep/CLAUDE.md")
        write_file(sb, "skills/x/assets/AGENTS.md")
        commit(sb)
        self.started(sb, "dirglob", {"ONE": {"scope": ["skills/x/scripts/**/*.py"]},
                                     "TWO": {"scope": ["skills/x/scripts/*.py"]}})
        lines = self.prompt(sb, "dirglob", "ONE")["prompt"].splitlines()
        at = lines.index(DIRS + " — read them:")
        self.assertEqual(lines[at + 1:at + 4], ["- skills/x/scripts/AGENTS.md", "- skills/x/scripts/lib/AGENTS.md",
                                                "- skills/x/scripts/lib/deep/CLAUDE.md"])
        self.assertNotIn("- skills/x/assets/AGENTS.md", lines)
        two = self.prompt(sb, "dirglob", "TWO")["prompt"]
        self.assertIn("\n- skills/x/scripts/AGENTS.md\n", two)
        self.assertNotIn("scripts/lib/AGENTS.md", two)

    def test_ten_records_and_a_directory_file_give_eleven_lines(self):
        sb = self.sandbox()
        names = [f"r{i:02d}" for i in range(10)]
        for name in names:
            write_record(sb, name, "skills/x/")
        write_index(sb, names)
        write_file(sb, "skills/x/AGENTS.md")
        commit(sb)
        self.started(sb, "eleven", {"ONE": {"scope": ["skills/x/a.py"]}})
        prompt = self.prompt(sb, "eleven", "ONE")["prompt"]
        pointers = [line for line in prompt.splitlines() if line.startswith("- ")]
        self.assertEqual(len(pointers), 11)
        self.assertEqual(pointers[-1], "- skills/x/AGENTS.md")
        self.assertNotIn("more, see", prompt)


class LimitTests(PointerCase):
    def test_twelve_records_give_ten_lines_in_index_order(self):
        sb = self.sandbox()
        names = [f"r{i:02d}" for i in range(12)]
        for name in names:
            write_record(sb, name, "skills/x/scripts/")
        write_index(sb, list(reversed(names)))
        commit(sb)
        self.started(sb, "many", {"ONE": {"scope": ["skills/x/scripts/prompts.py"]}})
        lines = self.prompt(sb, "many", "ONE")["prompt"].splitlines()
        at = lines.index(RECORDS + " — open the ones your work touches:")
        shown = lines[at + 1:at + 11]
        self.assertEqual([line.split("]")[0] for line in shown], [f"- [Record r{i:02d}" for i in range(11, 1, -1)])
        self.assertEqual(lines[at + 11], "+2 more, see docs/adr/index.md")

    def test_several_folders_link_their_own_files(self):
        sb = self.sandbox()
        write_file(sb, ".tasks/repo/profile.md", "---\nadr_folder: docs/adr\nadr_rules:\n"
                                                 "  - skills/x -> skills/x/adr\n---\n\n# Repo profile\n")
        flat = [f"f{i:02d}" for i in range(6)]
        local = [f"s{i:02d}" for i in range(6)]
        for name in flat:
            write_record(sb, name, "skills/x/")
        for name in local:
            write_record(sb, name, "skills/x/", folder="skills/x/adr")
        write_index(sb, flat)
        write_index(sb, local, folder="skills/x/adr")
        commit(sb)
        self.started(sb, "folders", {"ONE": {"scope": ["skills/x/"]}})
        prompt = self.prompt(sb, "folders", "ONE")["prompt"]
        self.assertIn("- [Record f00](docs/adr/f00.md)", prompt)
        self.assertIn("- [Record s00](skills/x/adr/s00.md)", prompt)
        self.assertIn("\n+2 more, see skills/x/adr/index.md\n", prompt)


class ReviewPointerTests(PointerCase):
    def reviewed(self, changed: str, rename: bool = False) -> tuple[Sandbox, str]:
        """A collected job ONE that changed `changed`, or (`rename`) moved prompts.py there unchanged."""
        sb = self.sandbox(points=["all-jobs"])
        write_record(sb, "prompts", "skills/x/scripts/prompts.py")
        write_record(sb, "assets", "skills/x/assets/")
        write_index(sb, ["prompts", "assets"])
        write_file(sb, "skills/x/scripts/prompts.py", "".join(f"line {i}\n" for i in range(40)))
        write_file(sb, "skills/x/scripts/AGENTS.md")
        commit(sb)
        task = self.started(sb, "rev", {"ONE": {}})
        ws = Path(self.prompt(sb, "rev", "ONE")["workspace"])
        (ws / changed).parent.mkdir(parents=True, exist_ok=True)
        if rename:
            sb.git("mv", "skills/x/scripts/prompts.py", changed, cwd=ws)
            sb.git("commit", "-q", "-m", "ONE: move", cwd=ws)
        else:
            sb.work(ws, changed, "changed\n", "ONE: work")
        sb.result(task, "jobs/ONE.result.md", status="done", summary="s", validation="pass", changes="made")
        sb.sae("collect", "rev", "ONE")
        return sb, task

    def test_job_review_matches_the_diff_and_the_command_carries_it(self):
        sb, _ = self.reviewed("skills/x/scripts/prompts.py")
        command = self.prompt(sb, "rev", "REVIEW-ONE", "--provider", "codex")["command"]
        line = "- [Record prompts](docs/adr/prompts.md) — Indexed decision of prompts."
        self.assertIn(line, command)
        prompt = self.prompt(sb, "rev", "REVIEW-ONE", "--resume", "--reason", "inline",
                             "--provider", "claude")["prompt"]
        self.assertIn(f"{RECORDS} — open the ones your work touches:\n{line}\n", prompt)
        self.assertNotIn("Record assets", prompt)

    def test_review_without_a_guarded_change_gets_no_lines(self):
        sb, _ = self.reviewed("notes/other.txt")
        prompt = self.prompt(sb, "rev", "REVIEW-ONE", "--provider", "claude")["prompt"]
        self.assertNotIn(RECORDS, prompt)
        self.assertNotIn(DIRS, prompt)

    def test_job_review_of_a_rename_matches_its_source(self):
        sb, _ = self.reviewed("moved/prompts.py", rename=True)
        prompt = self.prompt(sb, "rev", "REVIEW-ONE", "--provider", "claude")["prompt"]
        self.assertIn("- [Record prompts](docs/adr/prompts.md)", prompt)
        self.assertIn("\n- skills/x/scripts/AGENTS.md\n", prompt)

    def test_integration_review_matches_the_whole_task_diff(self):
        sb = self.sandbox()
        write_record(sb, "left", "left/")
        write_record(sb, "right", "right/")
        write_record(sb, "none", "none/")
        write_index(sb, ["left", "right", "none"])
        commit(sb)
        task = sb.new_task("whole", "whole")
        sb.sae("set", "whole", "review=integration")
        for job in ("LEFT", "RIGHT"):
            sb.sae("job", "add", "whole", job, "--kind", "implementation")
            sb.job_file(task, job)
        sb.approve_plan("whole")
        sb.sae("start", "whole")
        for job in ("LEFT", "RIGHT"):
            ws = Path(self.prompt(sb, "whole", job)["workspace"])
            (ws / job.lower()).mkdir()
            sb.work(ws, f"{job.lower()}/a.txt", "a\n", f"{job}: work")
            sb.result(task, f"jobs/{job}.result.md", status="done", summary="s", validation="pass", changes="made")
            sb.sae("collect", "whole", job)
        prompt = self.prompt(sb, "whole", "REVIEW-INTEGRATION", "--provider", "claude")["prompt"]
        self.assertIn("- [Record left](docs/adr/left.md)", prompt)
        self.assertIn("- [Record right](docs/adr/right.md)", prompt)
        self.assertNotIn("Record none", prompt)


    def test_integration_review_of_a_rename_matches_its_source(self):
        sb = self.sandbox()
        write_record(sb, "old", "old/a.txt")
        write_index(sb, ["old"])
        write_file(sb, "old/a.txt", "".join(f"line {i}\n" for i in range(40)))
        write_file(sb, "old/AGENTS.md")
        commit(sb)
        task = sb.new_task("moved", "moved")
        sb.sae("set", "moved", "review=integration")
        sb.sae("job", "add", "moved", "MOVE", "--kind", "implementation")
        sb.job_file(task, "MOVE")
        sb.approve_plan("moved")
        sb.sae("start", "moved")
        ws = Path(self.prompt(sb, "moved", "MOVE")["workspace"])
        (ws / "new").mkdir()
        sb.git("mv", "old/a.txt", "new/a.txt", cwd=ws)
        sb.git("commit", "-q", "-m", "MOVE: move", cwd=ws)
        sb.result(task, "jobs/MOVE.result.md", status="done", summary="s", validation="pass", changes="made")
        sb.sae("collect", "moved", "MOVE")
        prompt = self.prompt(sb, "moved", "REVIEW-INTEGRATION", "--provider", "claude")["prompt"]
        self.assertIn("- [Record old](docs/adr/old.md)", prompt)
        self.assertIn("\n- old/AGENTS.md\n", prompt)


class IndexPointerTests(PointerCase):
    def planner_prompt(self, sb: Sandbox, slug: str) -> str:
        task = sb.new_task(slug, slug)
        sb.approve_spec(slug)
        sb.sae("job", "add", slug, "PLAN", "--kind", "planning")
        sb.job_file(task, "PLAN", objective="Plan the jobs.")
        return self.prompt(sb, slug, "PLAN")["prompt"]

    def test_planner_gets_the_index_when_it_exists(self):
        sb = self.sandbox()
        write_record(sb, "one", "skills/x/")
        write_index(sb, ["one"])
        commit(sb)
        prompt = self.planner_prompt(sb, "planidx")
        self.assertIn(f"Decision-record index:                 {sb.repo / 'docs/adr/index.md'}\n", prompt)
        self.assertNotIn(RECORDS, prompt)

    def test_planner_without_an_index_gets_nothing(self):
        sb = self.sandbox()
        write_record(sb, "one", "skills/x/")
        commit(sb)
        self.assertNotIn("Decision-record index", self.planner_prompt(sb, "noidx"))

    def test_decision_worker_gets_the_index(self):
        sb = self.sandbox()
        write_record(sb, "one", "skills/x/")
        write_index(sb, ["one"])
        commit(sb)
        task = self.started(sb, "decide", {"ASK": {}})
        self.prompt(sb, "decide", "ASK")
        (sb.task_dir(task) / "jobs" / "ASK.result.md").write_text(
            "---\nstatus: parked\nsummary: needs a choice\nvalidation: not-run\nchanges: none\n---\n\n"
            "## Decision request\n**Decision required:** table or column?\n")
        sb.sae("collect", "decide", "ASK")
        job = sb.json("decision", "new", "decide", "--from", "ASK")["job"]
        prompt = self.prompt(sb, "decide", job)["prompt"]
        self.assertRegex(prompt, r"\nDecision-record index: +\S+/docs/adr/index\.md\n")


if __name__ == "__main__":
    unittest.main()
