"""ADR index: every ADR folder has an index.md that `sae adr accept` keeps current ([AMEND-ADR-INDEX])."""

from __future__ import annotations

import re
import unittest
from pathlib import Path

from saetest import REPO_ROOT, SaeTestCase

LINK = re.compile(r"^- \[[^\]]+\]\(([^)]+\.md)\)")


def index_problems(folder: Path) -> list[str]:
    """Files of an ADR folder without exactly one index line, and index links without a file."""
    index = folder / "index.md"
    if not index.is_file():
        return [f"{folder}: no index.md"]
    links = [m.group(1) for m in map(LINK.match, index.read_text().splitlines()) if m]
    files = sorted(str(p.relative_to(folder)) for p in folder.rglob("*.md") if p != index)
    problems = [f"{folder.name}/{f}: {links.count(f)} index lines" for f in files if links.count(f) != 1]
    problems += [f"{folder.name}/index.md links {link}, which does not exist"
                 for link in links if not (folder / link).is_file()]
    if links and links[0] != "_intent.md" and (folder / "_intent.md").exists():
        problems.append(f"{folder.name}/index.md: _intent.md is not the first line")
    return problems


def profile_adr_folders(root: Path) -> list[Path]:
    """The ADR folders that the repo profile of `root` names: its adr_rules targets and adr_folder."""
    text = (root / ".tasks" / "repo" / "profile.md").read_text()
    front = text.split("---\n")[1] if text.startswith("---\n") else ""
    names = re.findall(r"^\s*-\s*\S+\s*(?:->|→)\s*(\S+?)/?\s*$", front, re.M)
    names += re.findall(r"^adr_folder:\s*(\S+?)/?\s*$", front, re.M)
    return sorted({root / name for name in names})


class AdrIndexCheckTests(unittest.TestCase):
    def test_this_repository_indexes_every_adr_file(self):
        folders = profile_adr_folders(REPO_ROOT)
        self.assertTrue(folders)
        self.assertEqual([f for f in folders if not f.is_dir()], [])
        for folder in folders:
            self.assertEqual(index_problems(folder), [], folder.name)

    def test_the_check_names_a_missing_line_and_a_dangling_link(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            (folder / "_intent.md").write_text("# Intent\n")
            (folder / "2026-01-01-a.md").write_text("# A\n")
            (folder / "index.md").write_text("# Index\n\n- [Intent](_intent.md) — x\n- [B](2026-01-01-b.md) — y\n")
            problems = index_problems(folder)
            self.assertIn(f"{folder.name}/2026-01-01-a.md: 0 index lines", problems)
            self.assertIn(f"{folder.name}/index.md links 2026-01-01-b.md, which does not exist", problems)


class AdrAcceptIndexTests(SaeTestCase):
    def setUp(self):
        super().setUp()
        self.sb = self.sandbox()
        self.sb.new_task("drafts", "drafts")

    def draft(self, title: str, applies_to: str = "", decision: str = "") -> Path:
        args = ["adr", "new", "drafts", title, "--type", "architecture"]
        path = Path(self.sb.json(*args, *(["--applies-to", applies_to] if applies_to else []))["file"])
        if decision:
            path.write_text(path.read_text().replace("## Decision\n", f"## Decision\n{decision}\n", 1))
        return path

    def test_accept_creates_the_index_of_a_flat_folder_and_appends_lines(self):
        first = self.draft("Status is cached", decision="[joint] Status is cached for 60 s. It is cheap.")
        data = self.sb.json("adr", "accept", str(first))
        folder = self.sb.repo / "docs" / "decisions"
        self.assertEqual(Path(data["index"]), folder / "index.md")
        text = (folder / "index.md").read_text()
        self.assertTrue(text.startswith("# Index: decisions\n"))
        self.assertIn(f"- [Status is cached]({first.name}) — Status is cached for 60 s.\n", text)
        self.assertNotIn("_intent.md", text)
        second = self.draft("No retries")
        self.sb.json("adr", "accept", str(second))
        lines = (folder / "index.md").read_text().splitlines()
        self.assertEqual(lines[-2:], [f"- [Status is cached]({first.name}) — Status is cached for 60 s.",
                                      f"- [No retries]({second.name})"])
        self.assertEqual(index_problems(folder), [])

    def test_accept_into_a_rule_folder_keeps_intent_first_and_research_last(self):
        (self.sb.repo / ".tasks" / "repo").mkdir(parents=True, exist_ok=True)
        (self.sb.repo / ".tasks" / "repo" / "profile.md").write_text(
            "---\nadr_rules:\n  - skills/a/ -> docs/adr/a/\n---\n")
        folder = self.sb.repo / "docs" / "adr" / "a"
        (folder / "research").mkdir(parents=True)
        (folder / "_intent.md").write_text("# Intent: a\n")
        draft = self.draft("Use one queue", "skills/a/x.py", "Idea [human], design [joint]: one queue.")
        self.sb.json("adr", "accept", str(draft))
        lines = (folder / "index.md").read_text().splitlines()
        self.assertTrue(lines[-2].startswith("- [Intent: a](_intent.md) — "))
        self.assertEqual(lines[-1], f"- [Use one queue]({draft.name}) — One queue.")
        # an existing index with a research section: the record goes after the last record line
        (folder / "research" / "note.md").write_text("# Note\n")
        (folder / "index.md").write_text("\n".join(lines) + "\n\n## Research notes\n\n- [Note](research/note.md) — n\n")
        other = self.draft("Drop the cache", "skills/a/y.py")
        self.sb.json("adr", "accept", str(other))
        lines = (folder / "index.md").read_text().splitlines()
        self.assertEqual(lines[lines.index(f"- [Use one queue]({draft.name}) — One queue.") + 1],
                         f"- [Drop the cache]({other.name})")
        self.assertEqual(lines[-1], "- [Note](research/note.md) — n")
        self.assertEqual(index_problems(folder), [])


if __name__ == "__main__":
    unittest.main()
