"""OwlHermes Hermes Plugin — thin wrapper.

This file is the entry point that Hermes plugin loader calls.
It imports the real register() from the hermes_plugin package
so business logic stays in one place.

Since Hermes runs in its own Python environment (not the project .venv),
we add the project's .venv site-packages to sys.path so that
frontier_ai_risk_observer is importable.

Project-local plugins require HERMES_ENABLE_PROJECT_PLUGINS=true.
User plugins are enabled via `hermes plugins enable owlhermes`
or by adding 'owlhermes' to plugins.enabled in ~/.hermes/config.yaml.
"""
from __future__ import annotations

import sys
from pathlib import Path

# Resolve the project root from the symlink target.
# .hermes/plugins/owlhermes/ -> <project-root>/.hermes/plugins/owlhermes/
_plugin_dir = Path(__file__).resolve().parent
_project_root = _plugin_dir.parent.parent.parent

# Add project .venv site-packages to sys.path if not already present
_venv_site = _project_root / ".venv" / "lib"
if _venv_site.exists():
    for _sp in _venv_site.iterdir():
        _site_pkg = _sp / "site-packages"
        if _site_pkg.is_dir() and str(_site_pkg) not in sys.path:
            sys.path.insert(0, str(_site_pkg))

# Also add the project root itself (for editable installs)
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from frontier_ai_risk_observer.hermes_plugin.plugin import register  # noqa: E402

__all__ = ["register"]
