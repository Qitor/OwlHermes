# MCP Server Scaffold v2

This server exposes a small tool surface to Hermes-Agent and forwards requests to the backend REST API.

Run locally:

```bash
cd mcp_server_scaffold
uv run python server.py
```

Hermes config should include this server under `mcp_servers.ai_risk_signal`.

Do not put crawler/database logic here. Keep this as a safe MCP wrapper.
