"""Tests of the Codex catalog checks: exact versions and efforts in `setup save` and `doctor`,
and the doctor check that Codex families resolve.

Run from the repository root:  /usr/bin/python3 -m unittest discover -s tests
Every sandbox points SAE_CONFIG and CODEX_HOME into a temporary folder.
"""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from saetest import CODEX_CATALOG, EFFORTS, Sandbox, SaeTestCase, config_for, write_codex_catalog  # noqa: E402


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


if __name__ == "__main__":
    unittest.main()
