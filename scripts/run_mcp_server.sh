#!/usr/bin/env bash
# Wrapper script to launch the MCP stdio server.
# Used by Hermes as the MCP command to avoid -m flag parsing issues
# with `hermes mcp add --args`.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PYTHON="${SCRIPT_DIR}/../.venv/bin/python"
exec "$PYTHON" -m frontier_ai_risk_observer.mcp.server
