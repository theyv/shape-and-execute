"""Tests of the Codex catalog checks: exact versions and efforts in `setup save` and `doctor`,
the doctor check that Codex families resolve, and the setup proposal of `setup.md` ([AMEND-3]).

Run from the repository root:  /usr/bin/python3 -m unittest discover -s tests
Every sandbox points SAE_CONFIG and CODEX_HOME into a temporary folder.
"""

from __future__ import annotations

import json
import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from saetest import (CODEX_CATALOG, EFFORTS, SCRIPTS, SKILL_DIR, Sandbox, SaeTestCase,  # noqa: E402
                     config_for, write_codex_catalog)

sys.path.insert(0, str(SCRIPTS))
from sae_lib.config import LEVELS, PHASE_DIFFICULTIES, TIERS, validate_config  # noqa: E402
from sae_lib.setup_mode import config_skeleton  # noqa: E402


def with_codex_entry(sb: Sandbox, model: str, efforts: list) -> dict:
    """The sandbox config with one Codex exact entry added or replaced."""
    config = config_for(sb.worktrees)
    entries = [e for e in config["models"]["codex"] if e["model"] != model]
    entries.append({"model": model, "family": False, "enabled": True, "efforts": efforts})
    config["models"]["codex"] = entries
    return config


# The three cases of the finding: not offered, hidden, an effort the catalog does not list.
CASES = [("cx-9-typed", list(EFFORTS), "cx-9-typed is not in the Codex catalog"),
         ("cx-3-lite", list(EFFORTS), "cx-3-lite is hidden in the Codex catalog"),
         ("cx-1-lite", EFFORTS + ["ultra"], "the Codex catalog lists no effort 'ultra' for cx-1-lite")]


class CodexCatalogCheckTest(SaeTestCase):
    def doctor_checks(self, sb: Sandbox, code: int) -> list[dict]:
        return sb.json("doctor", code=code)["checks"]

    def test_setup_save_and_doctor_refuse_exact_versions_and_efforts_the_catalog_lacks(self):
        sb = self.sandbox()
        for model, efforts, message in CASES:
            with self.subTest(model=model):
                config = with_codex_entry(sb, model, efforts)
                out = sb.sae("setup", "save", stdin=json.dumps(config), code=1).stderr
                self.assertIn(message, " ".join(out.split()))
                sb.config.write_text(json.dumps(config))
                config_check = self.doctor_checks(sb, 2)[1]
                self.assertFalse(config_check["ok"])
                self.assertIn(message, config_check["text"])
        # a switched-off exact entry is not checked: it is never dispatched
        config = with_codex_entry(sb, "cx-9-typed", list(EFFORTS))
        config["models"]["codex"][-1]["enabled"] = False
        sb.sae("setup", "save", stdin=json.dumps(config))

    def test_without_a_catalog_exact_versions_are_validated_as_before(self):
        sb = self.sandbox()
        (sb.codex_home / "models_cache.json").unlink()
        sb.env["PATH"] = "/usr/bin:/bin"  # no codex CLI either
        for model, efforts, _ in CASES:
            with self.subTest(model=model):
                sb.sae("setup", "save", stdin=json.dumps(with_codex_entry(sb, model, efforts)))

    def test_doctor_checks_that_enabled_codex_families_resolve(self):
        sb = self.sandbox()
        checks = {c["text"]: c for c in self.doctor_checks(sb, 1)}  # 1: the subagent cap is not set
        self.assertTrue(checks["Codex family lite: resolves to cx-2-lite"]["ok"])
        self.assertTrue(checks["Codex family core: resolves to cx-2-core"]["ok"])
        # a catalog without any lite version, and the exact lite entry off: the family does not resolve
        write_codex_catalog(sb.codex_home, [m for m in CODEX_CATALOG if not m["slug"].endswith("-lite")])
        config = config_for(sb.worktrees)
        config["models"]["codex"][1]["enabled"] = False
        sb.config.write_text(json.dumps(config))
        checks = self.doctor_checks(sb, 1)
        lite = next(c for c in checks if c["text"].startswith("Codex family lite"))
        self.assertFalse(lite["ok"])
        self.assertIn("does not resolve (the Codex catalog lists no version)", lite["text"])
        self.assertIn("pin an exact version", lite["fix"])
        self.assertTrue(next(c for c in checks if c["text"].startswith("Codex family core"))["ok"])
        # a switched-off family is not checked
        config["models"]["codex"][0]["enabled"] = False
        for block in config["routing"]["codex"]["tiers"].values():
            if block["model"] == "lite":
                block["model"] = "core"
        sb.config.write_text(json.dumps(config))
        self.assertFalse(any(c["text"].startswith("Codex family lite") for c in self.doctor_checks(sb, 1)))


def setup_tables(section: str) -> dict:
    """Each Markdown table of a setup.md section: its header cell (first column) → header and rows."""
    tables = {}
    for block in re.findall(r"(?m)^(\|.*\|\n\|[-|]+\|\n(?:\|.*\|\n)+)", section):
        rows = [[c.strip() for c in line.strip("|").split("|")] for line in block.strip().splitlines()]
        tables[rows[0][0]] = (rows[0], rows[2:])
    return tables


class SetupProposalTest(unittest.TestCase):
    """[AMEND-3]: the proposal's cells carry only a tier, and the proposal saves as it stands."""

    def setUp(self):
        text = (SKILL_DIR / "references" / "modes" / "setup.md").read_text(encoding="utf-8")
        self.guide = text[text.index("## 2. Guide"):text.index("## 3. Propose")]
        self.proposal_text = text[text.index("## 3. Propose"):text.index("## 4. Save")]
        self.tables = setup_tables(self.proposal_text)

    def proposal(self) -> dict:
        """The schema-2 config that step 3 proposes: model lists, tiers (Tiers mode) and cells."""
        models, routing = {}, {}
        for harness, family, efforts in self.tables["harness"][1]:
            models.setdefault(harness.lower(), []).append(
                {"model": family, "family": True, "enabled": True, "efforts": efforts.split(", ")})
        for name, _, *pairs in self.tables["tier"][1]:
            for harness, pair in zip(("claude", "codex"), pairs):
                model, effort = pair.split(" · ")
                block = routing.setdefault(harness, {"tiers_in_cells": True, "tiers": {}, "tables": {}})
                block["tiers"][name] = {"model": model, "effort": effort}
        for harness, block in routing.items():
            for phase, columns in PHASE_DIFFICULTIES.items():
                header, rows = self.tables[f"{harness} · {phase}"]
                self.assertEqual(header[1:], list(columns), (harness, phase))
                self.assertEqual([r[0] for r in rows], list(LEVELS), (harness, phase))
                block["tables"][phase] = {row[0]: {d: {"tier": tier} for d, tier in zip(columns, row[1:])}
                                          for row in rows}
        return {"models": models, "routing": routing}

    def test_every_cell_is_a_tier_only(self):
        for harness in ("claude", "codex"):
            for phase in PHASE_DIFFICULTIES:
                for row in self.tables[f"{harness} · {phase}"][1]:
                    for cell in row[1:]:
                        self.assertIn(cell, TIERS, f"{harness} · {phase} · {row[0]}: {cell}")

    def test_the_proposal_saves_in_tiers_mode_and_names_only_listed_models_and_efforts(self):
        config = config_for(Path("/tmp/worktrees"))
        config.update(self.proposal())
        self.assertEqual(validate_config(config), [])
        for harness, block in config["routing"].items():
            listed = {m["model"]: m["efforts"] for m in config["models"][harness]}
            for name, tier in block["tiers"].items():
                self.assertIn(tier["effort"], listed.get(tier["model"], []), (harness, name))

    def test_the_guide_names_tiers_mode_and_free_mode(self):
        self.assertIn("Tiers mode (default, simpler)", self.guide)
        self.assertIn("Free mode: each cell has its own model + effort.", self.guide)

    def test_the_guide_keeps_a_blank_line_before_every_heading(self):
        body = self.guide[self.guide.index("```"):]
        lines = body.split("```")[1].strip("\n").splitlines()
        headings = [i for i, line in enumerate(lines) if line.startswith("#")]
        self.assertGreaterEqual(len(headings), 6)
        for i in headings[1:]:
            self.assertEqual(lines[i - 1], "", lines[i])
        self.assertIn("one blank line\nbefore every heading", self.guide)

    def test_the_gui_note_follows_the_routing_tables_heading(self):
        after = self.proposal_text.split("**Routing tables (Tiers mode)**", 1)[1]
        note = "!! YOU CAN CHANGE THIS MORE EASILY IN THE GUI LATER !!"
        self.assertIn(note, after[:after.index("|")])
        self.assertIn("in the\nconversation language", after[:after.index(note)])

    def test_the_skeleton_cells_carry_only_a_tier(self):
        facts = {"claude_on_path": True, "codex_on_path": False, "default_worktree_root": "/tmp/wt"}
        block = config_skeleton(facts)["routing"]["claude"]
        self.assertIs(block["tiers_in_cells"], True)
        cells = [c for p in block["tables"].values() for row in p.values() for c in row.values()]
        self.assertEqual({json.dumps(c) for c in cells}, {json.dumps({"tier": "<L1-L4>"})})


class SetupShowModeTest(SaeTestCase):
    def test_setup_show_names_the_routing_mode(self):
        sb = self.sandbox()
        self.assertIn("Tiers mode (tiers_in_cells on)", sb.sae("setup", "show").stdout)
        config = config_for(sb.worktrees)
        config["routing"]["claude"]["tiers_in_cells"] = False
        for phase in config["routing"]["claude"]["tables"].values():
            for row in phase.values():
                for cell in row.values():
                    cell.update(config["routing"]["claude"]["tiers"][cell["tier"]])
        sb.config.write_text(json.dumps(config))
        show = sb.sae("setup", "show").stdout
        self.assertIn("Free mode (tiers_in_cells off)", show)
        self.assertNotIn("tiers in cells", show)


if __name__ == "__main__":
    unittest.main()
