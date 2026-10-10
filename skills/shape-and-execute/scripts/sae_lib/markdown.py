"""Frontmatter, YAML scalars and Markdown sections."""

from __future__ import annotations

import re


def _strip_yaml_comment(line: str) -> str:
    quote, escaped = None, False
    for i, ch in enumerate(line):
        if escaped:
            escaped = False
        elif quote:
            if quote == '"' and ch == "\\":
                escaped = True
            elif ch == quote:
                quote = None
        elif ch in "'\"":
            quote = ch
        elif ch == "#" and (i == 0 or line[i - 1] in " \t"):
            return line[:i]
    return line


def _yaml_scalar(value: str):
    value = value.strip()
    if value.startswith("[") and value.endswith("]"):
        inner = value[1:-1].strip()
        if not inner:
            return []
        return [_yaml_scalar(part) for part in _split_inline_list(inner)]
    if len(value) >= 2 and value[0] == value[-1] == "'":
        return value[1:-1].replace("''", "'")
    if len(value) >= 2 and value[0] == value[-1] == '"':
        return _unescape_double(value[1:-1])
    if value in ("null", "~", ""):
        return None
    if value in ("true", "false"):
        return value == "true"
    if re.fullmatch(r"-?\d+", value):
        return int(value)
    return value


_DOUBLE_ESCAPES = {"\\": "\\", '"': '"', "n": "\n", "t": "\t", "/": "/", "0": "\0", "r": "\r"}


def _unescape_double(inner: str) -> str:
    """Decode a YAML double-quoted scalar body: `\\\\`, `\\"`, `\\n`, `\\t` (unknown escapes stay)."""
    out, i = [], 0
    while i < len(inner):
        ch = inner[i]
        if ch == "\\" and i + 1 < len(inner) and inner[i + 1] in _DOUBLE_ESCAPES:
            out.append(_DOUBLE_ESCAPES[inner[i + 1]])
            i += 2
            continue
        out.append(ch)
        i += 1
    return "".join(out)


def _split_inline_list(inner: str) -> list[str]:
    parts, current, quote, escaped = [], "", None, False
    for ch in inner:
        if escaped:
            current += ch
            escaped = False
        elif quote:
            current += ch
            if quote == '"' and ch == "\\":
                escaped = True
            elif ch == quote:
                quote = None
        elif ch in "'\"":
            quote = ch
            current += ch
        elif ch == ",":
            parts.append(current)
            current = ""
        else:
            current += ch
    parts.append(current)
    return [p.strip() for p in parts if p.strip()]


def split_frontmatter(text: str) -> tuple[dict, str]:
    """Returns (frontmatter, body). Supports `key: scalar`, `key: [a, b]` and block lists."""
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].rstrip("\r\n") != "---":
        return {}, text
    for end in range(1, len(lines)):
        if lines[end].rstrip("\r\n") == "---":
            break
    else:
        return {}, text
    data: dict = {}
    key = None
    for raw in lines[1:end]:
        line = _strip_yaml_comment(raw.rstrip("\r\n")).rstrip()
        if not line.strip():
            continue
        item = re.match(r"^\s*-\s+(.*)$", line)
        if item and key is not None and raw[:1] in (" ", "\t", "-"):
            if not isinstance(data.get(key), list):
                data[key] = []
            data[key].append(_yaml_scalar(item.group(1)))
            continue
        pair = re.match(r"^([A-Za-z_][\w-]*):\s*(.*)$", line)
        if pair:
            key = pair.group(1)
            data[key] = _yaml_scalar(pair.group(2))
    return data, "".join(lines[end + 1:])


def strip_html_comments(text: str) -> str:
    return re.sub(r"<!--.*?-->", "", text, flags=re.S)


def md_section(text: str, title: str, level: int = 2) -> str | None:
    """The text under the heading `<#*level> <title>` up to the next heading of the same or a
    higher level, or None when the heading is missing. Fenced code is not scanned."""
    out, inside, fence = [], False, False
    want = title.strip().lower()
    for line in text.splitlines():
        if line.lstrip().startswith("```"):
            fence = not fence
        m = None if fence else re.match(r"^(#{1,6})\s+(.*?)\s*#*\s*$", line)
        if m:
            depth = len(m.group(1))
            if inside and depth <= level:
                break
            if depth == level and m.group(2).strip().lower() == want:
                inside = True
                continue
        if inside:
            out.append(line)
    return "\n".join(out) if inside else None


def has_content(section: str | None) -> bool:
    if section is None:
        return False
    text = strip_html_comments(section)
    for line in text.splitlines():
        stripped = line.strip()
        if stripped and stripped not in ("-", "- [ ]", "*"):
            return True
    return False


def first_heading(text: str) -> str | None:
    for line in text.splitlines():
        m = re.match(r"^#\s+(.*)$", line)
        if m:
            return m.group(1).strip()
    return None
