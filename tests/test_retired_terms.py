"""Retired terms of shape-and-execute ([RETIRED-TERMS-TEST], [OUT-NEXT-STEP-CARD]).

The skill's files (SKILL.md, references, templates, agents, scripts, viewer assets) never use a
retired term. A hit fails with the file and the line. When you rename a term, add the old name
here. A term may be allowed in a named place where it is still correct.
"""

from __future__ import annotations

import re
import unittest

from saetest import SKILL_DIR

FOLDERS = ("SKILL.md", "references", "templates", "agents", "scripts", "assets")


def _schema1_conversion() -> str:
    """The body of convert_schema1: it reads schema-1 configs, so it names rungs and level maps."""
    text = (SKILL_DIR / "scripts/sae_lib/setup_mode.py").read_text(encoding="utf-8")
    start = text.index("def convert_schema1")
    return text[start:text.index("\ndef ", start)]


def _schema1_place(name: str, line: str) -> bool:
    """Where "rung" and "level map" still describe the schema-1 config: setup mode, a line that
    names schema 1 or 2, the schema-1 conversion and the viewer's fallback for old attempts."""
    return (name == "references/modes/setup.md"
            or re.search(r"schema[ -][12]", line) is not None
            or (name == "scripts/sae_lib/setup_mode.py" and line.strip() != "" and line in _schema1_conversion())
            or (name == "assets/viewer/app.js" and "old tasks" in line))


# (retired term, pattern, the place where it is still correct or None). Replaced terms first,
# then pointers to the removed design docs.
RETIRED = [
    ("rung", r"\brungs?\b", _schema1_place),
    ("level map", r"level[ _-]maps?", _schema1_place),
    ("model ladder", r"model ladder", None),
    ("task checkout", r"task checkout", None),
    ("execution checkout", r"execution checkout", None),
    ("wave", r"\bwaves?\b", None),
    ("context.md", r"context\.md", None),
    ("launch card", r"launch card", None),
    ("LAUNCH ·", r"LAUNCH ·", None),
    ("decision log entry", r"decision log entr", None),
    ("static viewer", r"\.viewer/index\.html", None),
    ("sae-cli.md", r"sae-cli\.md", None),
    ("wip-docs", r"wip-docs", None),
    ("design doc file", r"\b\d\d-(intent|principles|glossary|lifecycle|scaling|artifacts|cli-spec|execution"
                        r"|decisions-and-safety|quality-and-review|git-and-worktrees|models-settings-setup"
                        r"|viewer-spec|findings|team-readiness|decision-log|parking-lot|genesis-review)\b", None),
    ("DL-<n>", r"\bDL-\d+", None),
]


def scan(files) -> list[str]:
    """`<file>:<line>: <term>: <text>` for each retired term in (name, text) pairs."""
    hits = []
    for name, text in files:
        for n, line in enumerate(text.splitlines(), 1):
            for term, pattern, allowed in RETIRED:
                if re.search(pattern, line, re.I) and not (allowed and allowed(name, line)):
                    hits.append(f"{name}:{n}: {term}: {line.strip()}")
    return hits


def skill_files():
    for folder in FOLDERS:
        base = SKILL_DIR / folder
        paths = [base] if base.is_file() else sorted(base.rglob("*")) if base.is_dir() else []
        for path in paths:
            if path.is_file() and "__pycache__" not in path.parts:
                yield path.relative_to(SKILL_DIR).as_posix(), path.read_text(encoding="utf-8", errors="replace")


class RetiredTermsTests(unittest.TestCase):
    def test_skill_uses_no_retired_term(self):
        self.assertTrue((SKILL_DIR / "SKILL.md").is_file())
        self.assertEqual(scan(skill_files()), [])

    def test_a_retired_term_fails_with_file_and_line(self):
        text = "# Next step\n\nPrint the launch card.\n"
        self.assertEqual(scan([("references/modes/execute.md", text)]),
                         ["references/modes/execute.md:3: launch card: Print the launch card."])

    def test_rung_is_allowed_only_in_its_named_places(self):
        self.assertEqual(scan([("references/modes/setup.md", "each rung becomes a tier")]), [])
        self.assertEqual(len(scan([("references/modes/plan.md", "each rung becomes a tier")])), 1)


if __name__ == "__main__":
    unittest.main()
