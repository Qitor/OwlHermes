"""Deprecated compatibility launcher for the R1-06 MCP server.

The canonical implementation lives in ``frontier_ai_risk_observer.mcp.server``.
This file remains only so older local notes pointing at the scaffold fail less
surprisingly; new Hermes configs should launch the package module directly.
"""

from __future__ import annotations

from frontier_ai_risk_observer.mcp.server import mcp

if __name__ == "__main__":
    if mcp is None:
        raise RuntimeError(
            "Python MCP SDK is not installed. Launch "
            "`python -m frontier_ai_risk_observer.mcp.server` after installing it."
        )
    mcp.run()
