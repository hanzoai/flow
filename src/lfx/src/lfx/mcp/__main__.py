"""Entry point for the Flow MCP server.

Usage:
    python -m lfx.mcp
    # or via console script:
    lfx-mcp

Environment variables:
    FLOW_SERVER_URL: Flow server URL (default: http://localhost:7860)
    FLOW_API_KEY: API key for authentication (skips login)
"""

from lfx.mcp.server import mcp


def main():
    mcp.run()


if __name__ == "__main__":
    main()
