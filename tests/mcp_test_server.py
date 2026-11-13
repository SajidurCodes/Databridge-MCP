"""Launch the real MCP server against a test-only database."""

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

import mcp_server  # noqa: E402


if __name__ == "__main__":
    mcp_server.DATABASE_PATH = Path(sys.argv[1]).resolve()
    mcp_server.mcp.run(transport="stdio")