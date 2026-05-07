"""Skill registration for OwlHermes plugin.

Hermes plugins can reference skill directories. Skills are managed via the
`skills/` external_dirs mechanism in Hermes config. This module documents
the expected skill paths and provides a helper for skill path resolution.
"""

from __future__ import annotations

from pathlib import Path


def get_skills_dir() -> Path:
    """Return the path to the bundled skills directory.

    Skills are at: <repo_root>/skills/ai-risk-signal-observer/
    """
    # Skills are in the repo root, not in the plugin package
    repo_root = Path(__file__).resolve().parent.parent.parent.parent
    return repo_root / "skills"


def get_skill_paths() -> list[dict[str, str]]:
    """Return list of skill info dicts for documentation."""
    return [
        {
            "name": "ai-risk-signal-observer",
            "path": "skills/ai-risk-signal-observer/",
            "description": (
                "OwlHermes AI risk signal observer skill "
                "with plugin-first tool guidance"
            ),
        }
    ]
