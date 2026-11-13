"""DataBridge MCP server entry point."""

from pathlib import Path
from typing import Annotated, Literal

import pandas as pd
from mcp.server import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from pydantic import BaseModel, Field

from databridge.column_summary import ColumnSummaryError
from databridge.preview import DatasetPreview, preview_dataframe
from databridge.profiling import DatasetProfile, profile_dataframe
from databridge.storage import (
    DatasetInfo,
    DatasetNotFoundError,
    DatasetStore,
)
from databridge.summaries import (
    ColumnSummaryResult,
    SummaryMode,
    summarize_column_dataframe,
)


DATABASE_PATH = (
    Path(__file__).resolve().parent / "data" / "datasets.sqlite3"
)

DatasetId = Annotated[
    str,
    Field(
        pattern=r"^[0-9a-f]{32}$",
        description="Dataset ID returned by list_datasets.",
    ),
]

mcp = MCPServer("DataBridge MCP")


class ServerInfo(BaseModel):
    name: str
    status: Literal["development"]
    csv_tools_available: bool


class DatasetList(BaseModel):
    datasets: list[DatasetInfo]


def get_store() -> DatasetStore:
    """Use a database location independent of the working directory."""
    return DatasetStore(DATABASE_PATH)


def load_tool_dataframe(dataset_id: str) -> pd.DataFrame:
    """Translate an expected storage error into an MCP tool error."""
    try:
        return get_store().load_dataframe(dataset_id)
    except DatasetNotFoundError as exc:
        raise ToolError(
            "Dataset was not found. Use list_datasets to find available IDs."
        ) from exc


@mcp.tool()
def get_server_info() -> ServerInfo:
    """Report the server identity and whether CSV tools are implemented."""
    return ServerInfo(
        name="DataBridge MCP",
        status="development",
        csv_tools_available=True,
    )


@mcp.tool()
def list_datasets(
    limit: Annotated[
        int,
        Field(ge=1, le=100, description="Maximum datasets to return."),
    ] = 20,
) -> DatasetList:
    """List locally stored datasets, newest first, including their IDs."""
    return DatasetList(datasets=get_store().list_datasets(limit=limit))


@mcp.tool()
def profile_dataset(dataset_id: DatasetId) -> DatasetProfile:
    """Report row counts, column types, missing values, and duplicate rows."""
    return profile_dataframe(load_tool_dataframe(dataset_id))


@mcp.tool()
def preview_dataset(
    dataset_id: DatasetId,
    limit: Annotated[
        int,
        Field(ge=1, le=50, description="Maximum preview rows to return."),
    ] = 5,
) -> DatasetPreview:
    """Preview parsed rows as text, with null for missing values.

    Cells are limited to 200 characters. Truncation is reported.
    This is not a lossless CSV export.
    """
    return preview_dataframe(load_tool_dataframe(dataset_id), limit=limit)


@mcp.tool()
def summarize_column(
    dataset_id: DatasetId,
    column: Annotated[
        str,
        Field(min_length=1, description="Exact column name from the profile."),
    ],
    mode: SummaryMode,
    top_k: Annotated[
        int,
        Field(
            ge=1,
            le=20,
            description="Maximum categories; ignored in numeric mode.",
        ),
    ] = 5,
) -> ColumnSummaryResult:
    """Summarize one column using a predefined analysis mode.

    Numeric statistics exclude missing and infinite values and count them.
    Category percentages use nonmissing rows as the denominator.
    Category labels may be shortened, with truncation explicitly flagged.
    """
    frame = load_tool_dataframe(dataset_id)

    try:
        return summarize_column_dataframe(frame, column, mode, top_k)
    except ColumnSummaryError as exc:
        raise ToolError(str(exc)) from exc


if __name__ == "__main__":
    mcp.run(transport="stdio")