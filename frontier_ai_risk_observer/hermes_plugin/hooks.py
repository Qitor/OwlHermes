"""OwlHermes plugin hooks — initially minimal/no-op.

Hooks are registered with the Hermes plugin system and called at specific
lifecycle points. For now, we register no hooks. This can be extended later
for session start/end logging, tool call monitoring, etc.
"""

from __future__ import annotations

# No hooks registered in R1-15.
# Potential future hooks:
#   on_session_start — initialize DB connection pool
#   on_session_end — flush live vault buffers
#   post_tool_call — auto-mirror DB writes to Obsidian
