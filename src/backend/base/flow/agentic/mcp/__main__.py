"""Entry point for running the Flow Agentic MCP server.

This allows running the server with:
    python -m flow.agentic.mcp
"""

from flow.agentic.mcp.server import mcp

if __name__ == "__main__":
    mcp.run()
