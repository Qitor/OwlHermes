"""Safe Markdown utilities for Obsidian vault export.

All functions are pure — no file I/O, no network, no DB access.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any

BEGIN_MARKER = "<!-- BEGIN_AUTO_GENERATED: hermes-ai-risk-observer -->"
END_MARKER = "<!-- END_AUTO_GENERATED: hermes-ai-risk-observer -->"


@dataclass
class WriteResult:
    """Result of writing a generated note."""

    path: Path
    created: bool = True
    updated: bool = False
    preserved_human: bool = False


def slugify_filename(text: str) -> str:
    """Convert text to a filesystem-safe slug for note filenames."""
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode("ascii")
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[-\s]+", "-", text)
    text = text.strip("-")
    return text[:80] or "untitled"


def safe_filename(text: str) -> str:
    """Make text safe for use as a filename (preserves case)."""
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode("ascii")
    text = text.strip()
    text = re.sub(r'[<>:"/\\|?*]', "", text)
    text = re.sub(r"\s+", " ", text)
    return text[:100] or "untitled"


def render_frontmatter(data: dict[str, object]) -> str:
    """Render YAML frontmatter from a dict."""
    lines = ["---"]
    for key, value in sorted(data.items()):
        if value is None:
            lines.append(f"{key}:")
        elif isinstance(value, bool):
            lines.append(f"{key}: {str(value).lower()}")
        elif isinstance(value, list):
            if not value:
                lines.append(f"{key}: []")
            else:
                lines.append(f"{key}:")
                for item in value:
                    lines.append(f"  - {_yaml_scalar(item)}")
        elif isinstance(value, dict):
            lines.append(f"{key}:")
            for k, v in value.items():
                lines.append(f"  {k}: {_yaml_scalar(v)}")
        else:
            lines.append(f"{key}: {_yaml_scalar(value)}")
    lines.append("---")
    return "\n".join(lines)


def _yaml_scalar(value: object) -> str:
    """Format a scalar value for YAML."""
    if isinstance(value, bool):
        return str(value).lower()
    if isinstance(value, (int, float)):
        return str(value)
    s = str(value)
    if any(c in s for c in ":#{}[]|>!&*'\"\\\n"):
        escaped = s.replace('"', '\\"')
        return f'"{escaped}"'
    return s


def wikilink(title: str, alias: str | None = None) -> str:
    """Render an Obsidian wikilink."""
    if alias:
        return f"[[{title}|{alias}]]"
    return f"[[{title}]]"


def markdown_link(label: str, url: str) -> str:
    """Render a Markdown link."""
    return f"[{label}]({url})"


def atomic_write(path: Path, content: str) -> None:
    """Write content to a file atomically."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(content, encoding="utf-8")
    tmp.replace(path)


def replace_generated_block(existing: str, generated: str) -> str:
    """Replace generated block in existing content, preserving human content."""
    pattern = re.escape(BEGIN_MARKER) + r".*?" + re.escape(END_MARKER)
    replacement = f"{BEGIN_MARKER}\n{generated}\n{END_MARKER}"
    if re.search(pattern, existing, re.DOTALL):
        return re.sub(pattern, replacement, existing, flags=re.DOTALL)
    # No existing marker — append generated block
    return existing.rstrip() + "\n\n" + replacement + "\n"


def write_generated_note(
    path: Path,
    frontmatter: dict[str, Any],
    body: str,
    title: str,
) -> WriteResult:
    """Write a generated note, preserving human content outside markers."""
    generated_body = f"{BEGIN_MARKER}\n{body}\n{END_MARKER}"
    content = f"{render_frontmatter(frontmatter)}\n\n# {title}\n\n{generated_body}\n"

    result = WriteResult(path=path)

    if path.exists():
        existing = path.read_text(encoding="utf-8")
        if BEGIN_MARKER in existing:
            # Update only the generated block
            updated = replace_generated_block(existing, body)
            # Also update frontmatter — replace the old one
            updated = _update_frontmatter(updated, frontmatter)
            atomic_write(path, updated)
            result.updated = True
            result.preserved_human = True
            result.created = False
        else:
            # Human note without markers — append generated block
            appended = existing.rstrip() + "\n\n" + generated_body + "\n"
            atomic_write(path, appended)
            result.updated = True
            result.preserved_human = True
            result.created = False
    else:
        atomic_write(path, content)
        result.created = True
        result.updated = False

    return result


def _update_frontmatter(content: str, new_data: dict[str, object]) -> str:
    """Replace frontmatter in content with new data."""
    if not content.startswith("---"):
        return content
    end = content.find("---", 3)
    if end == -1:
        return content
    # Extract body after frontmatter
    body = content[end + 3:].lstrip("\n")
    return f"{render_frontmatter(new_data)}\n\n{body}"
