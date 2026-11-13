"""Verify preview serialization and validation over MCP stdio."""

import asyncio
import sys
from pathlib import Path

from mcp import Client, StdioServerParameters
from mcp.types import TextContent

from databridge.storage import DatasetStore


def test_mcp_preview_workflow(tmp_path: Path) -> None:
    database_path = tmp_path / "datasets.sqlite3"
    info = DatasetStore(database_path).add_csv(
        "preview.csv",
        b"name,age\nNila,24\nRafi,\nMina,30\n",
    )

    launcher = Path(__file__).with_name("mcp_test_server.py").resolve()
    server = StdioServerParameters(
        command=sys.executable,
        args=[str(launcher), str(database_path)],
    )

    async def check_workflow() -> None:
        async with asyncio.timeout(45):
            async with Client(server) as client:
                tools = await client.list_tools()
                assert "preview_dataset" in {
                    tool.name for tool in tools.tools
                }

                result = await client.call_tool(
                    "preview_dataset",
                    {"dataset_id": info.dataset_id, "limit": 2},
                )
                assert result.is_error is False
                assert result.structured_content == {
                    "columns": ["name", "age"],
                    "rows": [["Nila", "24"], ["Rafi", None]],
                    "total_rows": 3,
                    "returned_rows": 2,
                    "has_more_rows": True,
                    "truncated_cells": 0,
                }

                invalid = await client.call_tool(
                    "preview_dataset",
                    {"dataset_id": info.dataset_id, "limit": 51},
                )
                assert invalid.is_error is True

                missing = await client.call_tool(
                    "preview_dataset",
                    {"dataset_id": "0" * 32},
                )
                assert missing.is_error is True
                message = "\n".join(
                    block.text
                    for block in missing.content
                    if isinstance(block, TextContent)
                )
                assert "Dataset was not found" in message

                default = await client.call_tool(
                    "preview_dataset",
                    {"dataset_id": info.dataset_id},
                )
                assert default.is_error is False
                assert default.structured_content is not None
                assert default.structured_content["returned_rows"] == 3
                assert default.structured_content["has_more_rows"] is False

    asyncio.run(check_workflow())