"""DataBridge MCP server entry point."""

from typing import Literal

from mcp.server import MCPServer
from pydantic import BaseModel


mcp = MCPServer("DataBridge MCP")


class ServerInfo(BaseModel):
    """Information about this early development build."""

    name: str
    status: Literal["development"]
    csv_tools_available: bool


@mcp.tool()
def get_server_info() -> ServerInfo:
    """Report the server identity and whether CSV tools are implemented."""
    return ServerInfo(
        name="DataBridge MCP",
        status="development",
        csv_tools_available=False,
    )


if __name__ == "__main__":
    mcp.run(transport="stdio")