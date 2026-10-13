"""Backlog subfolders: the listings show items of `.tasks/backlog/` and of one level of
subfolders (for example one per module), with no flag or setting.

Run from the repository root:  /usr/bin/python3 -m unittest discover -s tests -v
"""

from __future__ import annotations

import unittest

from saetest import SaeTestCase


class BacklogSubfolderTests(SaeTestCase):
    def test_items_in_a_subfolder_are_listed(self):
        sb = self.sandbox()
        sb.sae("new", "Flat item", "--backlog")
        sb.sae("new", "Skill item", "--backlog")
        moved = next((sb.repo / ".tasks/backlog").glob("*--skill-item.md"))
        (sb.repo / ".tasks/backlog/my-skill").mkdir()
        moved.rename(sb.repo / ".tasks/backlog/my-skill" / moved.name)
        listed = sb.json("status")["backlog"]
        self.assertEqual(sorted(b["title"] for b in listed), ["Flat item", "Skill item"])
        self.assertIn(".tasks/backlog/my-skill/", " ".join(b["file"] for b in listed))


if __name__ == "__main__":
    unittest.main()
