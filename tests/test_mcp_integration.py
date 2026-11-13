"""Verify MCP behavior across a real stdio subprocess."""

import asyncio
import sys
from pathlib import Path

from mcp import Client, StdioServerParameters
from mcp.types import TextContent

from databridge.storage import DatasetStore


def test_mcp_dataset_workflow(tmp_path: Path) -> None:
    database_path = tmp_path / "datasets.sqlite3"
    store = DatasetStore(database_path)
    info = store.add_csv(
        "integration.csv",
        b"name,age\nAmina,20\nAmina,20\nRafi,\nMina,\n",
    )

    launcher = Path(__file__).with_name("mcp_test_server.py").resolve()
    server = StdioServerParameters(
        command=sys.executable,
        args=[str(launcher), str(database_path)],
    )

    async def check_workflow() -> None:
        # Bound connection, requests, and normal cleanup.
        async with asyncio.timeout(45):
            async with Client(server) as client:
                discovered = await client.list_tools()
                names = {tool.name for tool in discovered.tools}
                assert {
                    "get_server_info",
                    "list_datasets",
                    "profile_dataset",
                } <= names

                listing = await client.call_tool("list_datasets", {})
                assert listing.is_error is False
                assert listing.structured_content is not None
                datasets = listing.structured_content["datasets"]
                assert len(datasets) == 1
                assert datasets[0]["dataset_id"] == info.dataset_id
                assert datasets[0]["filename"] == "integration.csv"

                result = await client.call_tool(
                    "profile_dataset",
                    {"dataset_id": info.dataset_id},
                )
                assert result.is_error is False
                assert result.structured_content is not None
                profile = result.structured_content
                assert profile["row_count"] == 4
                assert profile["column_count"] == 2
                assert profile["duplicate_row_count"] == 1

                columns = {
                    column["name"]: column
                    for column in profile["columns"]
                }
                assert columns["age"]["missing_count"] == 2
                assert columns["age"]["missing_percent"] == 50.0

                missing = await client.call_tool(
                    "profile_dataset",
                    {"dataset_id": "0" * 32},
                )
                assert missing.is_error is True
                message = "\n".join(
                    block.text
                    for block in missing.content
                    if isinstance(block, TextContent)
                )
                assert "Dataset was not found" in message
                assert "list_datasets" in message

                invalid_limit = await client.call_tool(
                    "list_datasets",
                    {"limit": 101},
                )
                assert invalid_limit.is_error is True

                malformed_id = await client.call_tool(
                    "profile_dataset",
                    {"dataset_id": "../secret"},
                )
                assert malformed_id.is_error is True

                # A failed request must not prevent later valid calls.
                recovery = await client.call_tool("get_server_info", {})
                assert recovery.is_error is False
                assert recovery.structured_content is not None
                assert recovery.structured_content["csv_tools_available"] is True

    asyncio.run(check_workflow())