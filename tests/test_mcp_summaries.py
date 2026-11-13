"""Verify column summaries through a real MCP subprocess."""

import asyncio
import sys
from pathlib import Path

from mcp import Client, StdioServerParameters
from mcp.types import TextContent

from databridge.storage import DatasetStore


def test_mcp_summary_workflow(tmp_path: Path) -> None:
    database_path = tmp_path / "datasets.sqlite3"
    info = DatasetStore(database_path).add_csv(
        "summary.csv",
        b"city,age\nDhaka,20\nDhaka,30\nSylhet,\n",
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
                assert "summarize_column" in {
                    tool.name for tool in tools.tools
                }

                numeric = await client.call_tool(
                    "summarize_column",
                    {
                        "dataset_id": info.dataset_id,
                        "column": "age",
                        "mode": "numeric",
                    },
                )
                assert numeric.is_error is False
                assert numeric.structured_content is not None
                assert numeric.structured_content["mode"] == "numeric"
                summary = numeric.structured_content["summary"]
                assert summary["mean"] == 25
                assert summary["median"] == 25
                assert summary["missing_count"] == 1
                assert summary["finite_count"] == 2

                categorical = await client.call_tool(
                    "summarize_column",
                    {
                        "dataset_id": info.dataset_id,
                        "column": "city",
                        "mode": "categorical",
                        "top_k": 1,
                    },
                )
                assert categorical.is_error is False
                assert categorical.structured_content is not None
                assert categorical.structured_content["mode"] == "categorical"
                summary = categorical.structured_content["summary"]
                assert summary["top_values"][0]["value"] == "Dhaka"
                assert summary["top_values"][0]["count"] == 2
                assert summary["other_count"] == 1

                for column, expected in [
                    ("city", "real numeric"),
                    ("unknown", "not found"),
                ]:
                    result = await client.call_tool(
                        "summarize_column",
                        {
                            "dataset_id": info.dataset_id,
                            "column": column,
                            "mode": "numeric",
                        },
                    )
                    assert result.is_error is True
                    message = "\n".join(
                        block.text
                        for block in result.content
                        if isinstance(block, TextContent)
                    )
                    assert expected in message

                invalid_mode = await client.call_tool(
                    "summarize_column",
                    {
                        "dataset_id": info.dataset_id,
                        "column": "age",
                        "mode": "execute_python",
                    },
                )
                assert invalid_mode.is_error is True

    asyncio.run(check_workflow())