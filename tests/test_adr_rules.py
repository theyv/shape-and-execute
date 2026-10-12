"""ADR rules: `sae adr accept` routes a record to the folder of its path ([ADR-RULES])."""

from __future__ import annotations

from pathlib import Path

from saetest import SKILL_DIR, SaeTestCase

REPO_ROOT = SKILL_DIR.parents[1]
RULES = ("---\nadr_rules:\n  - skills/shape-and-execute/ -> docs/adr/\n"
         "  - skills/shape-and-execute/scripts/ -> docs/adr/sae-scripts/\n"
         "  - skills/other-skill/ -> docs/adr/other-skill/\n---\n")


class AdrRulesTests(SaeTestCase):
    def setUp(self):
        super().setUp()
        self.sb = self.sandbox()
        self.sb.new_task("drafts", "drafts")

    def profile(self, text: str) -> None:
        (self.sb.repo / ".tasks" / "repo").mkdir(parents=True, exist_ok=True)
        (self.sb.repo / ".tasks" / "repo" / "profile.md").write_text(text)

    def draft(self, applies_to: str, title: str = "Cache status") -> Path:
        args = ["adr", "new", "drafts", title, "--type", "architecture"]
        return Path(self.sb.json(*args, *(["--applies-to", applies_to] if applies_to else []))["file"])

    def accept(self, draft: Path, code: int = 0):
        return self.sb.json("adr", "accept", str(draft)) if code == 0 else self.sb.sae("adr", "accept", str(draft), code=code)

    def test_this_repository_routes_sae_paths_to_its_folder(self):
        self.profile((REPO_ROOT / ".tasks" / "repo" / "profile.md").read_text())
        data = self.accept(self.draft("skills/shape-and-execute/scripts/sae.py"))
        self.assertEqual(Path(data["file"]).parent, self.sb.repo / "docs" / "adr" / "shape-and-execute")
        data = self.accept(self.draft("skills/other-skill/SKILL.md,LifeCycle", "Other"))
        self.assertEqual(Path(data["file"]).parent, self.sb.repo / "docs" / "adr" / "other-skill")

    def test_longest_prefix_wins_and_prefixes_match_whole_segments(self):
        self.profile(RULES)
        data = self.accept(self.draft("./skills/shape-and-execute/scripts/sae_lib/findings.py"))
        self.assertEqual(Path(data["file"]).parent, self.sb.repo / "docs" / "adr" / "sae-scripts")
        # both paths fall under rules of one folder; a name that is no path is ignored
        data = self.accept(self.draft("skills/other-skill,skills/other-skill/SKILL.md,Term", "Two"))
        self.assertEqual(Path(data["file"]).parent, self.sb.repo / "docs" / "adr" / "other-skill")
        # skills/shape-and-execute-extra/ is not under skills/shape-and-execute/: the flat folder
        # (here the existing docs/adr/ that the rules above created)
        data = self.accept(self.draft("skills/shape-and-execute-extra/x.py", "Three"))
        self.assertEqual(Path(data["file"]).parent, self.sb.repo / "docs" / "adr")

    def test_no_match_falls_back_to_the_flat_folder(self):
        self.profile(RULES.replace("---\n", "---\nadr_folder: records/adr\n", 1))
        data = self.accept(self.draft("src/status"))
        self.assertEqual(Path(data["file"]).parent, self.sb.repo / "records" / "adr")
        data = self.accept(self.draft("", "No paths"))
        self.assertEqual(Path(data["file"]).parent, self.sb.repo / "records" / "adr")

    def test_a_draft_under_two_folders_is_refused_with_both_named(self):
        """[EDGE-ADR-TWO-RULES]"""
        self.profile(RULES)
        draft = self.draft("skills/shape-and-execute/SKILL.md,skills/other-skill/SKILL.md")
        err = " ".join(self.accept(draft, code=1).stderr.split())
        self.assertIn("docs/adr, docs/adr/other-skill", err)
        self.assertIn("Narrow applies-to or split the draft", err)
        self.assertTrue(draft.exists())
        self.assertFalse((self.sb.repo / "docs").exists())

    def test_invalid_rules_are_refused_and_doctor_names_them(self):
        self.profile("---\nadr_rules:\n  - skills/a/ -> docs/adr/a/\n  - skills/b/\n---\n")
        err = " ".join(self.accept(self.draft("skills/a/x"), code=1).stderr.split())
        self.assertIn("'skills/b/'", err)
        out = " ".join(self.sb.sae("doctor", "--repo", code=1).stdout.split())
        self.assertIn("✗ ADR rules in the repo profile: 1 valid; adr_rules item 'skills/b/'", out)
        self.profile(RULES)
        out = " ".join(self.sb.sae("doctor", "--repo", code=1).stdout.split())  # other checks may fail here
        self.assertIn("✓ ADR rules in the repo profile: 3 valid", out)

    def test_template_and_setup_show_both_forms(self):
        template = (SKILL_DIR / "templates" / "repo" / "profile.md").read_text()
        self.assertIn("adr_folder:", template)
        self.assertIn("adr_rules:", template)
        setup = (SKILL_DIR / "references" / "modes" / "setup.md").read_text()
        step7 = setup[setup.index("## 7."):setup.index("## Later changes")]
        for form in ("one flat folder", "rules per path", "adr_folder", "adr_rules"):
            self.assertIn(form, step7)
