"""Project Stakes: lookup order, the block in every dispatch prompt, `sae status`, the profile writer.

[STAKES-LOOKUP], [STAKES-POINTER], [STAKES-ASK], [AMEND-1], [AMEND-2].
Run from the repository root:  python3 tests/run.py test_stakes
"""

from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from saetest import MIN_SPEC, SCRIPTS, Sandbox, SaeTestCase, SKILL_DIR  # noqa: E402

sys.path.insert(0, str(SCRIPTS))
from sae_lib import prompts, stakes  # noqa: E402

HEADER = "Project Stakes: how much care this project needs (from "
NOT_SET = "Project Stakes: how much care this project needs. Not set, so set the bar yourself"
FILLED = ("- Who uses it and why: Friends, on weekends.\n- Acceptable breakage: Any.\n"
          "- What matters now: Speed.\n- Don't build:\n- So build it like: A toy.\n")
EMPTY_LABELS = ("- Who uses it and why:\n- Acceptable breakage:   <!-- one or two sentences -->\n"
                "- What matters now:\n- Don't build:           <!-- optional -->\n- So build it like:      <!-- a toy -->\n")


def section(body: str, heading: str = "Project Stakes") -> str:
    return f"# Repo profile\n\n## {heading}\n{body}\n## Validation commands\n- Smoke: `true`\n"


class StakesCase(SaeTestCase):
    def home(self) -> Sandbox:
        sb = self.sandbox()
        (sb.repo / ".tasks" / "repo").mkdir(parents=True, exist_ok=True)
        return sb

    def profile(self, sb: Sandbox, body: str | None = None, heading: str = "Project Stakes") -> Path:
        path = sb.repo / ".tasks" / "repo" / "profile.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(section(body, heading) if body is not None else "# Repo profile\n")
        return path

    def instructions(self, sb: Sandbox, name: str, body: str, heading: str = "Project Stakes") -> Path:
        path = sb.repo / name
        path.write_text(f"# Rules\n\nSome rule.\n\n## {heading}\n{body}\n## Other\ntext\n")
        return path

    def block(self, sb: Sandbox) -> str:
        return stakes.prompt_block(sb.repo)


class LookupTests(StakesCase):
    def test_sources_are_read_in_order_and_the_first_with_content_wins(self):
        sb = self.home()
        self.assertIsNone(stakes.find_stakes(sb.repo))
        claude = self.instructions(sb, "CLAUDE.md", "- From CLAUDE.md.\n")
        self.assertEqual(stakes.find_stakes(sb.repo).path, claude)
        agents = self.instructions(sb, "AGENTS.md", "- From AGENTS.md.\n")
        self.assertEqual(stakes.find_stakes(sb.repo).path, agents)
        profile = self.profile(sb, "- From the profile.\n")
        found = stakes.find_stakes(sb.repo)
        self.assertEqual((found.path, found.text, found.in_profile), (profile, "- From the profile.", True))
        profile.unlink()
        self.assertEqual(stakes.find_stakes(sb.repo).path, agents)

    def test_an_empty_section_is_skipped(self):
        sb = self.home()
        agents = self.instructions(sb, "AGENTS.md", "- From AGENTS.md.\n")
        for body in (EMPTY_LABELS, "", "<!-- only a comment\nover two lines -->\n", "\n\n"):
            self.profile(sb, body)
            self.assertEqual(stakes.find_stakes(sb.repo).path, agents, body)

    def test_the_not_set_line_and_prose_are_content(self):
        sb = self.home()
        self.instructions(sb, "AGENTS.md", "- From AGENTS.md.\n")
        profile = self.profile(sb, "- Not set by the owner. Set the bar yourself.\n")
        self.assertEqual(stakes.find_stakes(sb.repo).path, profile)
        self.profile(sb, "A toy for a kid. Anything may break.\n")
        self.assertEqual(stakes.find_stakes(sb.repo).text, "A toy for a kid. Anything may break.")

    def test_one_label_with_a_value_is_content_and_empty_labels_are_left_out(self):
        sb = self.home()
        self.profile(sb, EMPTY_LABELS.replace("- What matters now:", "- What matters now: Speed."))
        self.assertEqual(stakes.find_stakes(sb.repo).text, "- What matters now: Speed.")

    def test_there_is_no_fallback_to_the_old_section_name(self):
        sb = self.home()
        self.profile(sb, "- Old name.\n", heading="Stakes")
        self.instructions(sb, "AGENTS.md", "- Old name.\n", heading="Stakes")
        self.assertIsNone(stakes.find_stakes(sb.repo))

    def test_a_deeper_heading_stays_inside_the_section_and_a_comment_example_is_ignored(self):
        sb = self.home()
        path = self.profile(sb, "<!-- Example:\n     - Who uses it and why: A kid. -->\n- Real.\n### Detail\nMore.\n")
        self.assertEqual(stakes.find_stakes(sb.repo).text, "- Real.\n### Detail\nMore.")
        self.assertEqual(stakes.section_text(path).splitlines()[0], "- Real.")

    def test_frontmatter_comments_are_not_headings(self):
        sb = self.home()
        path = self.profile(sb)
        path.write_text("---\n# artifact_language: en\n---\n\n# Repo profile\n\n## Project Stakes\n- Real.\n")
        self.assertEqual(stakes.find_stakes(sb.repo).text, "- Real.")


class BlockTests(StakesCase):
    def test_the_block_is_the_header_and_the_section_text(self):
        sb = self.home()
        profile = self.profile(sb, "<!-- help -->\n" + FILLED)
        block = self.block(sb)
        header = prompts.STAKES_LINE.format(path=profile)
        self.assertTrue(block.startswith(header + "\n"))
        self.assertIn(f'(from {profile}, section "Project Stakes"). Work to this bar.', header)
        self.assertEqual(block[len(header) + 1:], "- Who uses it and why: Friends, on weekends.\n"
                         "- Acceptable breakage: Any.\n- What matters now: Speed.\n- So build it like: A toy.")
        self.assertNotIn("help", block)

    def test_a_section_of_more_than_15_lines_is_named_instead_of_pasted(self):
        sb = self.home()
        profile = self.profile(sb, "".join(f"- Line {i}.\n" for i in range(16)))
        block = self.block(sb)
        self.assertNotIn("Line 1", block)
        self.assertEqual(block, prompts.STAKES_LINE.format(path=profile)[:-1] + "."
                         + prompts.STAKES_LONG_SUFFIX.format(limit=15))
        self.assertEqual(len(block.splitlines()), 1)
        self.profile(sb, "".join(f"- Line {i}.\n" for i in range(15)))
        self.assertIn("- Line 14.", self.block(sb))

    def test_without_stakes_the_block_is_the_not_set_text(self):
        sb = self.home()
        block = self.block(sb)
        self.assertEqual(block, prompts.STAKES_NOT_SET_LINE)
        self.assertTrue(block.startswith(NOT_SET))
        self.assertIn("who uses it, what breakage is acceptable and what matters now", block)
        self.assertNotIn("estimate", block)

    def test_the_texts_name_the_section_and_hold_no_pointer_to_other_copies(self):
        self.assertIn('section "Project Stakes"', prompts.STAKES_LINE)
        for text in (prompts.STAKES_LINE, prompts.STAKES_NOT_SET_LINE):
            self.assertTrue(text.startswith("Project Stakes:"))
            self.assertNotIn("copy", text)
            self.assertNotIn("\n", text)
            self.assertIn("Leaving out what the bar does not need is expected, not a failure. "
                          "They never lower the requirements you were given", text)
            self.assertNotIn("edge cases", text)

    def test_the_template_not_set_line_has_the_not_set_meaning(self):
        text = (SKILL_DIR / "templates" / "repo" / "profile.md").read_text()
        self.assertNotIn("neither over- nor under-engineer", text)
        flat = " ".join(text.split())
        self.assertIn("Not set by the owner. Set the bar yourself", flat)
        self.assertIn("Leaving out what it does not need is expected; it never lowers the requirements you "
                      "were given", flat)


class AskTests(unittest.TestCase):
    """INTEGRATION-FIX-5: shaping asks for the Project Stakes bullet by bullet, with the example."""

    def test_the_shaping_question_names_the_section_lists_the_bullets_and_shows_the_example(self):
        shape = (SKILL_DIR / "references" / "modes" / "shape.md").read_text()
        template = (SKILL_DIR / "templates" / "repo" / "profile.md").read_text()
        flat = " ".join(shape.split())
        self.assertIn("goes into the Project Stakes section of `.tasks/repo/profile.md`", flat)
        self.assertIn("every agent reads it", flat)
        for label in ("Who uses it and why", "Acceptable breakage", "What matters now",
                      "Don't build (optional)", "So build it like"):
            self.assertIn(label, shape)
        example = re.findall(r"(?m)^ +(- [^:\n]+: .+)$", template.split("## Project Stakes")[1].split("Do not name")[0])
        self.assertEqual(len(example), 5)
        for line in example:
            self.assertIn(line.strip(), shape)
        self.assertIn('"not set" line', shape)

class PromptKindTests(StakesCase):
    def count(self, text: str) -> int:
        return text.count("Project Stakes: how much care this project needs")

    def test_every_prompt_kind_carries_exactly_one_stakes_block(self):
        sb = self.sandbox(points=["spec"])
        profile = self.profile(sb, FILLED)
        task = sb.new_task("kinds", "kinds")
        (sb.task_dir(task) / "specs.md").write_text(MIN_SPEC)
        sb.sae("approve", "kinds", "spec", code=3)  # the spec review is due
        prompts_by_kind = {"review": sb.json("dispatch", "kinds", "REVIEW-SPEC", "--provider", "claude")["prompt"],
                           "review COMMAND": sb.json("dispatch", "kinds", "REVIEW-SPEC", "--provider", "codex",
                                                     "--resume", "--reason", "again")["command"]}
        sb.result(task, "reviews/REVIEW-SPEC.md", target="spec", verdict="pass")
        sb.sae("collect", "kinds", "REVIEW-SPEC")
        sb.sae("approve", "kinds", "spec")
        early = sb.new_task("early", "early")  # a research job runs while the task is shaped
        sb.sae("job", "add", "early", "RESEARCH", "--kind", "research")
        sb.job_file(early, "RESEARCH")
        prompts_by_kind["research"] = sb.json("dispatch", "early", "RESEARCH")["prompt"]
        sb.sae("job", "add", "kinds", "WORK", "--kind", "implementation")
        sb.job_file(task, "WORK")
        sb.sae("approve", "kinds", "plan")
        sb.sae("start", "kinds")
        data = sb.json("dispatch", "kinds", "WORK")
        prompts_by_kind["worker"] = data["prompt"]
        sb.result(task, "jobs/WORK.result.md", status="parked", summary="needs a choice", validation="not-run",
                  changes="none")
        with (sb.task_dir(task) / "jobs" / "WORK.result.md").open("a") as handle:
            handle.write("## Decision request\n**Decision required:** table or column?\n")
        sb.sae("collect", "kinds", "WORK")
        decision = sb.json("decision", "new", "kinds", "--from", "WORK")["job"]
        prompts_by_kind["decision"] = sb.json("dispatch", "kinds", decision)["prompt"]
        for kind, prompt in prompts_by_kind.items():
            self.assertEqual(self.count(prompt), 1, kind)
            self.assertIn(str(profile), prompt, kind)
        self.assertIn("- Who uses it and why: Friends, on weekends.", prompts_by_kind["worker"])
        self.assertNotIn("Not set, so set the bar", "".join(prompts_by_kind.values()))

    def test_the_planner_prompt_carries_one_stakes_block(self):
        sb = self.home()
        self.profile(sb, FILLED)
        task = sb.new_task("planner", "planner")
        sb.approve_spec("planner")
        sb.sae("job", "add", "planner", "PLAN", "--kind", "planning")
        sb.job_file(task, "PLAN")
        prompt = sb.json("dispatch", "planner", "PLAN")["prompt"]
        self.assertEqual(self.count(prompt), 1)
        self.assertIn("- So build it like: A toy.", prompt)

    def test_a_prompt_without_stakes_carries_the_not_set_text_once(self):
        sb = self.home()
        task = sb.new_task("plain", "plain")
        sb.sae("job", "add", "plain", "R1", "--kind", "research")
        sb.job_file(task, "R1")
        prompt = sb.json("dispatch", "plain", "R1")["prompt"]
        self.assertEqual(prompt.count(NOT_SET), 1)
        self.assertEqual(self.count(prompt), 1)

    def test_a_resumed_prompt_still_has_one_block(self):
        sb = self.home()
        self.profile(sb, FILLED)
        task = sb.new_task("again", "again")
        sb.sae("job", "add", "again", "R1", "--kind", "research")
        sb.job_file(task, "R1")
        sb.sae("dispatch", "again", "R1")
        prompt = sb.json("dispatch", "again", "R1", "--resume", "--reason", "more")["prompt"]
        self.assertEqual(self.count(prompt), 1)


class HomeProfileTests(StakesCase):
    def test_a_task_worktree_reads_and_names_the_home_profile(self):
        sb = self.home()
        profile = self.profile(sb, FILLED)
        task = sb.new_task("exec", "exec")
        sb.sae("job", "add", "exec", "ONE", "--kind", "implementation")
        sb.job_file(task, "ONE")
        sb.approve_plan("exec")
        sb.sae("start", "exec")
        worktree = sb.task_worktree(task)
        self.assertNotEqual(worktree, sb.repo)
        (worktree / ".tasks" / "repo").mkdir(parents=True, exist_ok=True)
        (worktree / ".tasks" / "repo" / "profile.md").write_text(section("- A stale copy.\n"))
        status = sb.sae("status", "exec").stdout
        self.assertIn(f"Project Stakes: {profile}\n", status)
        prompt = sb.json("dispatch", "exec", "ONE")["prompt"]
        self.assertIn(str(profile), prompt)
        self.assertNotIn("A stale copy", prompt)
        # a viewer edit during execution reaches the next dispatch
        stakes.save_profile_stakes(sb.repo, "- Edited while the task runs.")
        resumed = sb.json("dispatch", "exec", "ONE", "--resume", "--reason", "again")["prompt"]
        self.assertIn("- Edited while the task runs.", resumed)
        self.assertNotIn("Friends, on weekends", resumed)

    def test_a_task_made_in_a_linked_worktree_names_the_main_worktrees_profile(self):
        sb = self.home()
        profile = self.profile(sb)
        profile.write_text(section("- From main.\n"))
        other = self.tmp / "other"
        sb.git("worktree", "add", "-q", "-b", "side", str(other))
        (other / ".tasks" / "repo").mkdir(parents=True, exist_ok=True)
        (other / ".tasks" / "repo" / "profile.md").write_text(section("- From the linked copy.\n"))
        task = sb.json("new", "Side", "--slug", "side", cwd=other)["task"]
        data = sb.json("status", "side", cwd=other)
        self.assertEqual(data["stakes"], {"source": str(profile), "profile": str(profile)})
        self.assertIn(f"Project Stakes: {profile}", sb.sae("status", "side", cwd=other).stdout)
        sb.sae("job", "add", "side", "R1", "--kind", "research", cwd=other)
        (other / ".tasks" / task / "jobs").mkdir(exist_ok=True)
        (other / ".tasks" / task / "jobs" / "R1.md").write_text("---\nid: R1\n---\n\n# R1\n\n## Objective\nLook.\n")
        stakes.save_profile_stakes(other, "- Saved from the linked worktree.")
        self.assertIn("Saved from the linked worktree", profile.read_text())
        self.assertIn("From the linked copy", (other / ".tasks" / "repo" / "profile.md").read_text())
        prompt = sb.json("dispatch", "side", "R1", cwd=other)["prompt"]
        self.assertIn("- Saved from the linked worktree.", prompt)
        self.assertNotIn("From the linked copy", prompt)


class StatusTests(StakesCase):
    def test_status_names_the_source_or_says_not_set_with_the_profile_path(self):
        sb = self.home()
        sb.new_task("st", "st")
        profile = sb.repo / ".tasks" / "repo" / "profile.md"
        out = " ".join(sb.sae("status", "st").stdout.split())
        self.assertIn(f'Project Stakes: not set (write them to {profile}, section "Project Stakes")', out)
        self.assertEqual(sb.json("status", "st")["stakes"], {"source": None, "profile": str(profile)})
        agents = self.instructions(sb, "AGENTS.md", "- Rules.\n")
        self.assertIn(f"Project Stakes: {agents}\n", sb.sae("status", "st").stdout)
        self.profile(sb, "- Not set by the owner. Set the bar yourself.\n")  # a skip: the profile is the source
        self.assertIn(f"Project Stakes: {profile}\n", sb.sae("status", "st").stdout)

    def test_status_writes_nothing(self):
        sb = self.home()
        sb.new_task("quiet", "quiet")
        before = sb.git("status", "--porcelain", "--untracked-files=all")
        sb.sae("status", "quiet")
        self.assertEqual(sb.git("status", "--porcelain", "--untracked-files=all"), before)
        self.assertFalse((sb.repo / ".tasks" / "repo" / "profile.md").exists())


class WriterTests(StakesCase):
    TEMPLATE = (SKILL_DIR / "templates" / "repo" / "profile.md").read_text()

    def lines_outside(self, text: str) -> list[str]:
        """The profile without its Project Stakes section."""
        found = stakes._find_section(text.split("\n"))
        lines = text.split("\n")
        return lines if not found else lines[:found[0]] + lines[found[1]:]

    def test_the_writer_replaces_only_the_section_and_keeps_the_help_comment(self):
        sb = self.home()
        path = sb.repo / ".tasks" / "repo" / "profile.md"
        path.write_text(self.TEMPLATE)
        before = path.read_text()
        self.assertEqual(stakes.save_profile_stakes(sb.repo, FILLED), path)
        after = path.read_text()
        self.assertEqual(self.lines_outside(after), self.lines_outside(before))
        self.assertIn("Example, a small game for a kid:", after)  # the template's help comment stays
        self.assertEqual(stakes.find_stakes(sb.repo).text, FILLED.replace("- Don't build:\n", "").strip())
        stakes.save_profile_stakes(sb.repo, "- Second save.")
        again = path.read_text()
        self.assertEqual(self.lines_outside(again), self.lines_outside(before))
        self.assertEqual(stakes.find_stakes(sb.repo).text, "- Second save.")
        self.assertEqual(again.count("## Project Stakes"), 1)

    def test_a_section_in_the_middle_and_at_the_end(self):
        sb = self.home()
        path = sb.repo / ".tasks" / "repo" / "profile.md"
        path.write_text("---\nadr_folder: x\n---\n\n# Repo profile\n\n## Hot files\n-\n\n## Project Stakes\n- Old.\n")
        stakes.save_profile_stakes(sb.repo, "- New.")
        self.assertEqual(path.read_text(), "---\nadr_folder: x\n---\n\n# Repo profile\n\n## Hot files\n-\n\n"
                                           "## Project Stakes\n- New.\n")
        path.write_text(section("- Old.\n"))
        stakes.save_profile_stakes(sb.repo, "- New.")
        self.assertEqual(path.read_text(), section("- New.\n"))

    def test_a_missing_section_is_added_before_the_first_other_section(self):
        sb = self.home()
        path = sb.repo / ".tasks" / "repo" / "profile.md"
        old = "---\nadr_folder: x\n---\n\n# Repo profile\n\n<!-- Facts. -->\n\n## Validation commands\n- Smoke: `x`\n"
        path.write_text(old)
        stakes.save_profile_stakes(sb.repo, "- Added.")
        self.assertEqual(path.read_text(), old.replace("## Validation commands",
                                                       "## Project Stakes\n- Added.\n\n## Validation commands"))
        path.write_text("# Repo profile\n\ntext without sections\n")
        stakes.save_profile_stakes(sb.repo, "- Added.")
        self.assertEqual(path.read_text(), "# Repo profile\n\ntext without sections\n\n## Project Stakes\n- Added.\n")

    def test_a_missing_profile_is_created(self):
        sb = self.sandbox()
        path = stakes.save_profile_stakes(sb.repo, "- Fresh.")
        self.assertEqual(path.read_text(), "# Repo profile\n\n## Project Stakes\n- Fresh.\n")

    def test_the_writer_never_touches_agents_or_claude_md(self):
        sb = self.home()
        agents = self.instructions(sb, "AGENTS.md", "- Rules.\n")
        before = agents.read_bytes()
        stakes.save_profile_stakes(sb.repo, "- Saved.")
        self.assertEqual(agents.read_bytes(), before)
        self.assertFalse((sb.repo / "CLAUDE.md").exists())
        self.assertEqual(stakes.find_stakes(sb.repo).path, sb.repo / ".tasks" / "repo" / "profile.md")

    def test_text_with_a_section_heading_is_refused(self):
        sb = self.home()
        with self.assertRaises(ValueError):
            stakes.save_profile_stakes(sb.repo, "- One.\n## Hot files\n- Two.")
        self.assertFalse((sb.repo / ".tasks" / "repo" / "profile.md").exists())

    def test_text_with_an_unclosed_code_fence_is_refused_and_the_next_section_stays(self):
        # REVIEW-INTEGRATION 1: an open fence would hide `## Validation commands`, and the next save would delete it
        sb = self.home()
        path = self.profile(sb, "- Old.\n")
        before = path.read_bytes()
        with self.assertRaisesRegex(ValueError, "code fence"):
            stakes.save_profile_stakes(sb.repo, "- Example:\n```\nmake smoke")
        self.assertEqual(path.read_bytes(), before)
        # a closed fence, also one holding a heading line, keeps the next section
        stakes.save_profile_stakes(sb.repo, "- Example:\n```\n## not a section\n```")
        stakes.save_profile_stakes(sb.repo, "- Corrected.")
        self.assertEqual(path.read_text(), section("- Corrected.\n"))

    def test_a_stored_section_with_an_unclosed_code_fence_is_never_overwritten(self):
        # the stored section's end is ambiguous: a save would replace every section after the fence
        sb = self.home()
        path = self.profile(sb, "- Example:\n```\nmake smoke\n")
        before = path.read_bytes()
        with self.assertRaisesRegex(ValueError, "code fence"):
            stakes.save_profile_stakes(sb.repo, "- Corrected.")
        self.assertEqual(path.read_bytes(), before)
        self.assertIn("## Validation commands", path.read_text())


if __name__ == "__main__":
    unittest.main()
