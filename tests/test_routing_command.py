"""`sae routing <harness>`: the model and effort for a subagent, with project overrides.

Run from the repository root:  python3 tests/run.py test_routing_command
"""

from __future__ import annotations

import unittest

from saetest import SaeTestCase


class RoutingCommandCase(SaeTestCase):
    def test_balanced_cells_and_project_override(self):
        sb = self.sandbox()
        cells = sb.json("routing", "claude")["cells"]
        self.assertEqual(cells["execution"]["hard"], {"model": "c-big", "effort": "high"})
        self.assertEqual(set(cells), {"research", "planning", "execution", "review"})
        self.assertEqual(cells["execution"]["easy"], cells["execution"]["mechanical"])  # easy falls back

        sb.sae("project", "set", "routing.claude.execution.balanced.hard=L1")
        out = sb.sae("routing", "claude").stdout
        self.assertIn("Execution subagent (writing code):", out)
        self.assertIn("Never stronger than your own model and effort", out)
        self.assertRegex(out, r"hard\s+model=c-small\s+effort=medium")

    def test_level_flag(self):
        sb = self.sandbox()
        data = sb.json("routing", "codex", "--level", "economy")
        self.assertEqual(data["level"], "economy")
        self.assertEqual(set(data["cells"]["review"]), {"normal", "hard"})


if __name__ == "__main__":
    unittest.main()
