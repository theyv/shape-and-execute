"""Project Stakes: where they are read from, the block of every dispatch prompt, the profile writer.

[STAKES-LOOKUP], [STAKES-POINTER], [AMEND-1], [AMEND-2]. One profile for every reader and writer:
`.tasks/repo/profile.md` of the main worktree, also while a task runs in its task worktree.
Reading happens at dispatch and status time, so a viewer edit reaches the next dispatch.
`sae` never writes AGENTS.md or CLAUDE.md.
"""

from __future__ import annotations

import contextlib
import hashlib
import os
import re
import tempfile
from dataclasses import dataclass
from pathlib import Path

from .gitutil import main_worktree
from .markdown import strip_html_comments

SECTION_TITLE = "Project Stakes"
INSTRUCTION_FILES = ("AGENTS.md", "CLAUDE.md")  # read after the profile, in this order
LONG_SECTION_LINES = 15  # a longer section is named in the prompt, not pasted
# The five labels of the profile template's section; a line with a label and no value is empty.
LABELS = ("Who uses it and why", "Acceptable breakage", "What matters now", "Don't build", "So build it like")
_LABEL_ONLY = re.compile(r"^\s*[-*]?\s*(?:" + "|".join(re.escape(l).replace("'", "['’]") for l in LABELS)
                         + r")\s*:\s*$", re.I)
_HEADING = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")


@dataclass
class Stakes:
    path: Path   # the file that holds the section
    text: str    # the section without HTML comments and without empty label lines

    @property
    def in_profile(self) -> bool:
        return self.path.name == "profile.md"


def read_stored(path: Path, default: str | None = None) -> str | None:
    """`path` as stored, line endings included (`common.read_text` turns CRLF into LF): every
    reader here splits on "\\n", so a CRLF line keeps its "\\r", which `section_revision` hashes
    and `save_profile_stakes` writes back."""
    try:
        return path.read_bytes().decode("utf-8")
    except FileNotFoundError:
        return default


def profile_path(root: Path) -> Path:
    """The one profile: `.tasks/repo/profile.md` of the main worktree of `root`'s repository."""
    return main_worktree(root) / ".tasks" / "repo" / "profile.md"


def _body_start(lines: list[str]) -> int:
    """The first line after the frontmatter (0 without frontmatter)."""
    if lines and lines[0].rstrip("\r") == "---":
        for end in range(1, len(lines)):
            if lines[end].rstrip("\r") == "---":
                return end + 1
    return 0


def _is_fence(line: str) -> bool:
    return line.lstrip().startswith("```")


def _headings(lines: list[str]):
    """(index, depth, title) of every heading line outside the frontmatter. Code fences are not
    parsed: an unbalanced fence anywhere in the file would make a fence-aware reader take the
    wrong line for a section end, and a save would delete the sections it skipped (REVIEW-INTEGRATION
    findings 1, REVIEW-INTEGRATION-2 finding 1). A `# comment` line inside a fenced example reads
    as a heading here; that can only cut a section short, never make it swallow the next one."""
    for index in range(_body_start(lines), len(lines)):
        match = _HEADING.match(lines[index])
        if match:
            yield index, len(match.group(1)), match.group(2).strip()


def _find_section(lines: list[str]) -> tuple[int, int] | None:
    """(heading line, end line) of the level-2 Project Stakes section; the end is the next
    heading of level 1 or 2, or the end of the file."""
    start = None
    for index, depth, title in _headings(lines):
        if start is not None and depth <= 2:
            return start, index
        if start is None and depth == 2 and title.lower() == SECTION_TITLE.lower():
            start = index
    return (start, len(lines)) if start is not None else None


def section_text(path: Path) -> str | None:
    """The Project Stakes section of a Markdown file with HTML comments stripped and blank edges
    trimmed; None when the file or the section is missing."""
    text = read_stored(path, None)
    return None if text is None else _section_text(text)


def _section_text(text: str) -> str | None:
    lines = text.split("\n")
    found = _find_section(lines)
    if not found:
        return None
    body = strip_html_comments("\n".join(lines[found[0] + 1:found[1]]))
    out: list[str] = []
    for line in (l.rstrip() for l in body.split("\n")):
        if line or (out and out[-1]):  # collapse runs of blank lines
            out.append(line)
    return "\n".join(out).strip("\n")


def section_revision(path: Path) -> str:
    """A revision of the Project Stakes section exactly as stored (heading to end, comments and
    spaces included): a SHA-256 of its raw text, "" when the file or the section is missing. Any
    change to the stored section changes it, also one that `section_text` strips."""
    return _section_revision(read_stored(path, None) or "")


def _section_revision(text: str) -> str:
    lines = text.split("\n")
    found = _find_section(lines)
    if not found:
        return ""
    return hashlib.sha256("\n".join(lines[found[0]:found[1]]).encode()).hexdigest()


def section_and_revision(path: Path) -> tuple[str | None, str]:
    """`section_text` and `section_revision` of one read of `path`: a save between two reads can
    never pair an old section with the revision of a newer one."""
    text = read_stored(path, None)
    return (None, "") if text is None else (_section_text(text), _section_revision(text))


def _content(text: str) -> str:
    """`text` without empty label lines; "" when nothing else is left."""
    kept = "\n".join(line for line in text.split("\n") if not _LABEL_ONLY.match(line))
    return kept.strip("\n") if kept.strip() else ""


def find_stakes(root: Path) -> Stakes | None:
    """The Project Stakes of the repository of `root`: the profile's section, then AGENTS.md's,
    then CLAUDE.md's, all in the main worktree. The first section with content wins; None when none
    has ([STAKES-LOOKUP], [AMEND-2])."""
    home = main_worktree(root)
    for path in (profile_path(root), *(home / name for name in INSTRUCTION_FILES)):
        text = section_text(path)
        if text is not None and _content(text):
            return Stakes(path, _content(text))
    return None


def status_line(root: Path, found: Stakes | None) -> str:
    """The `sae status` line for the result of `find_stakes`: the source, or `not set` with the
    profile path to write them to."""
    if found:
        return f"Project Stakes: {found.path}"
    return f'Project Stakes: not set (write them to {profile_path(root)}, section "{SECTION_TITLE}")'


# The question printed while Project Stakes are not set ([AMEND-4]); the profile template's example.
ASK_EXAMPLE = """\
- Who uses it and why: A game for a kid to play in the evenings.
- Acceptable breakage: Any. We restart and laugh; at worst a high score is lost.
- What matters now: Speed. We are still finding out what is fun.
- Don't build: Save-file versioning or recovery for nearly impossible races.
- So build it like: A toy."""


def ask_text(root: Path) -> str:
    """The explanation and the question about the Project Stakes, printed by `sae status` only
    while they are not set. Shaping and setup show it and ask it; neither keeps a copy."""
    path = profile_path(root)
    return "\n".join([
        f'Question for the owner: Project Stakes ({SECTION_TITLE} section of {path})',
        "Project Stakes say how much care this project needs. Every worker builds to that bar and every",
        "reviewer judges the work against it; that is what they are for. You set them once per repository.",
        "They are kept in `.tasks/repo/profile.md`; edit them later in the GUI or in the file.",
        "Ask the five bullets one by one. For each, show your draft from AGENTS.md or CLAUDE.md and the",
        "README; where they say nothing, propose your best guess. The owner confirms or corrects.",
        "  1. Who uses it and why?",
        "  2. Acceptable breakage: how much, in one or two sentences?",
        "  3. What matters now?",
        "  4. Don't build (optional): what have agents already overbuilt here?",
        "  5. So build it like: a toy, a tool for friends, a product people pay for, or a bank?",
        "A model answer, for a small game for a kid:",
        *(f"    {line}" for line in ASK_EXAMPLE.split("\n")),
        "The owner may skip this: the profile then gets the \"not set\" line, agents set the bar themselves",
        "from the repository, and the question is not asked again.",
        f"Write the answer to {path}, section \"{SECTION_TITLE}\". On a skip, write the profile",
        'template\'s "not set" line there.',
    ])


def prompt_block(root: Path) -> str:
    """The one stakes block of a dispatch prompt ([STAKES-POINTER], [AMEND-1]): the header and the
    section text, the header and the source of a long section, or the "not set" text."""
    from .prompts import STAKES_LINE, STAKES_LONG_SUFFIX, STAKES_NOT_SET_LINE  # prompts imports this module
    found = find_stakes(root)
    if not found:
        return STAKES_NOT_SET_LINE
    header = STAKES_LINE.format(path=found.path)
    if len(found.text.split("\n")) > LONG_SECTION_LINES:
        return header[:-1] + "." + STAKES_LONG_SUFFIX.format(limit=LONG_SECTION_LINES)
    return f"{header}\n{found.text}"


def save_profile_stakes(root: Path, text: str) -> Path:
    """Replace the Project Stakes section of the profile with `text` and return the profile path.

    Only that section changes: the bytes of every other line stay, line endings included, and the
    new lines take the CRLF or LF of the section heading (or the first line). A comment right under the
    heading (the template's help) is kept. A missing section is added where the template puts
    it, before the first other `##` section; a missing profile is created. The rule that keeps
    every other byte: the section runs from its heading to the next line that starts a heading of
    level 1 or 2, with no fence parsing. Raises ValueError, and writes nothing, when `text` holds
    such a heading or a code fence line, and when the stored section holds a code fence line (its
    reader-visible end may then lie inside a fenced example)."""
    body = text.replace("\r\n", "\n").strip("\n")
    if any(_is_fence(line) for line in body.split("\n")):
        raise ValueError(f"The {SECTION_TITLE} text cannot hold a code fence line (```): the profile reader does "
                         "not parse fences, so a fenced line that starts with # would end the section. "
                         "Write the example as plain text or an inline `code` span.")
    if any(d <= 2 for _, d, _ in _headings(body.split("\n"))):
        raise ValueError(f"The {SECTION_TITLE} text cannot hold a heading of level 1 or 2.")
    path = profile_path(root)
    lines = (read_stored(path, "") or "").split("\n")
    if lines == [""]:
        lines = ["# Repo profile", ""]
    found = _find_section(lines)
    if found and any(_is_fence(line) for line in lines[found[0] + 1:found[1]]):
        raise ValueError(f"The {SECTION_TITLE} section in {path} holds a code fence line (```), so its end may lie "
                         "inside a fenced example and a save would leave the rest of that example behind. Remove "
                         "the fence in the file, reload, and save again.")
    # The lines this save adds take the line ending of the section heading, or of the first line.
    cr = "\r" if (lines[found[0]] if found else lines[0]).endswith("\r") else ""
    new = [f"## {SECTION_TITLE}{cr}", *(f"{line}{cr}" for line in (body.split("\n") if body else [])), cr]
    if found:
        start, end = found
        keep = _leading_comment(lines, start + 1, end)
        lines[start:end] = [lines[start], *keep, *new[1:]]
    else:
        before = next((i for i, d, _ in _headings(lines) if d == 2), None)
        if before is None:
            tail = lines[:-1] if lines[-1] == "" else lines
            lines = tail + ([cr] if tail and tail[-1].rstrip("\r") else []) + new
        else:
            lines[before:before] = ([cr] if before and lines[before - 1].strip() else []) + new
    if lines[-1] == "\r":  # the last empty line ends the file
        lines[-1] = ""
    _write_stored(path, "\n".join(lines))
    return path


def _write_stored(path: Path, text: str) -> None:
    """Write `text` atomically with its line endings as they are (`common.write_atomic` writes in
    text mode, which on Windows turns every "\\n" into CRLF, also one that already has its "\\r")."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(text.encode("utf-8"))
        os.replace(tmp, path)
    except BaseException:
        with contextlib.suppress(FileNotFoundError):
            os.unlink(tmp)
        raise


def _leading_comment(lines: list[str], start: int, end: int) -> list[str]:
    """The HTML comment that follows the section heading, blank lines before it included."""
    at = start
    while at < end and not lines[at].strip():
        at += 1
    if at >= end or not lines[at].lstrip().startswith("<!--"):
        return []
    while at < end and "-->" not in lines[at]:
        at += 1
    return lines[start:at + 1] if at < end else []
