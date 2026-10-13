"""The spec is the only source of requirement IDs: every `## Requirements…` heading counts, the
intent's `## Acceptance` does not, and a task without a spec or without requirements fails the check.

Run from the repository root:  /usr/bin/python3 -m unittest discover -s tests -v
Spec: [REQ-ONE-SOURCE], [REQ-GROUPED-HEADINGS], [SPEC-REQUIRED].
"""

from __future__ import annotations

import unittest

from saetest import SaeTestCase


class SpecSourceTests(SaeTestCase):
    def test_a_task_without_specs_md_fails_check_and_spec_approval(self):
        sb = self.sandbox(points=["plan"])
        sb.new_task("No spec", "no-spec")
        errors = sb.json("check", "no-spec", code=3)["errors"]
        self.assertTrue(any("specs.md is missing" in e and "## Requirements" in e for e in errors), errors)
        self.assertIn("specs.md is missing", sb.sae("approve", "no-spec", "spec", code=3).stderr)

    def test_a_spec_without_requirements_fails_check_and_spec_approval(self):
        sb = self.sandbox(points=["plan"])
        task = sb.new_task("Empty spec", "empty-spec")
        (sb.task_dir(task) / "specs.md").write_text(
            "# Spec\n\n## Summary\n### [NOT-A-REQ] outside requirements\n\n## Requirements\n"
            "<!-- ### [COMMENTED] no -->\n")
        errors = sb.json("check", "empty-spec", code=3)["errors"]
        self.assertTrue(any("no requirements" in e and "### [ID]" in e for e in errors), errors)
        self.assertIn("no requirements", sb.sae("approve", "empty-spec", "spec", code=3).stderr)

    def test_grouped_requirement_headings_all_count(self):
        sb = self.sandbox(points=["plan"])
        task = sb.new_task("Groups", "groups")
        (sb.task_dir(task) / "specs.md").write_text(
            "# Spec\n\n## Requirements: a\n\n### [A-ONE] One\n- [ ] one\n\n## Notes\n### [NOTE-ID] not a requirement\n\n"
            "## Requirements: b\n\n### [B-TWO] Two\n- [ ] two\n")
        self.assertEqual(sb.json("check", "groups")["errors"], [])
        sb.approve_spec("groups")
        sb.sae("job", "add", "groups", "WORK", "--kind", "implementation")
        sb.job_file(task, "WORK", verify=["true"])
        errors = "\n".join(sb.json("check", "groups", code=3)["errors"])
        self.assertIn("requirement [A-ONE] is not covered", errors)
        self.assertIn("requirement [B-TWO] is not covered", errors)
        self.assertNotIn("NOTE-ID", errors)
        sb.job_file(task, "WORK", covers=["A-ONE", "B-TWO"], verify=["true"])
        self.assertEqual(sb.json("check", "groups")["errors"], [])

    def test_the_same_id_in_two_groups_is_a_duplicate(self):
        sb = self.sandbox(points=["plan"])
        task = sb.new_task("Dup groups", "dup-groups")
        (sb.task_dir(task) / "specs.md").write_text(
            "# Spec\n\n## Requirements: a\n\n### [SAME] One\n- [ ] one\n\n"
            "## Requirements: b\n\n### [SAME] Again\n- [ ] two\n")
        errors = sb.json("check", "dup-groups", code=3)["errors"]
        self.assertIn("specs.md: duplicate ID [SAME]", errors)

    def test_the_intents_acceptance_adds_no_requirement(self):
        sb = self.sandbox(points=["plan"])
        task = sb.new_task("Intent acceptance", "intent-acc")
        (sb.task_dir(task) / "intent.md").write_text("# Intent\n\n## Acceptance\n- [INTENT-ONLY] from the intent\n")
        (sb.task_dir(task) / "specs.md").write_text("# Spec\n\n## Requirements\n\n### [ONE] One\n- [ ] one\n")
        sb.approve_spec("intent-acc")
        sb.sae("job", "add", "intent-acc", "WORK", "--kind", "implementation")
        sb.job_file(task, "WORK", covers=["ONE", "INTENT-ONLY"], verify=["true"])
        errors = sb.json("check", "intent-acc", code=3)["errors"]
        self.assertEqual(errors, ["WORK: covers [INTENT-ONLY], which does not exist"])


if __name__ == "__main__":
    unittest.main()
