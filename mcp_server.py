"""DataBridge MCP server entry point."""

from pathlib import Path
from typing import Annotated, Literal

from mcp.server import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from pydantic import BaseModel, Field

from databridge.preview import DatasetPreview, preview_dataframe
from databridge.profiling import DatasetProfile, profile_dataframe
from databridge.storage import (
    DatasetInfo,
    DatasetNotFoundError,
    DatasetStore,
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
    """Information about this development build."""

    name: str
    status: Literal["development"]
    csv_tools_available: bool


class DatasetList(BaseModel):
    """A bounded list of stored datasets, newest first."""

    datasets: list[DatasetInfo]


def get_store() -> DatasetStore:
    """Use a database location independent of the working directory."""
    return DatasetStore(DATABASE_PATH)


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
    try:
        frame = get_store().load_dataframe(dataset_id)
    except DatasetNotFoundError as exc:
        raise ToolError(
            "Dataset was not found. Use list_datasets to find available IDs."
        ) from exc

    return profile_dataframe(frame)


@mcp.tool()
def preview_dataset(
    dataset_id: DatasetId,
    limit: Annotated[
        int,
        Field(ge=1, le=50, description="Maximum preview rows to return."),
    ] = 5,
) -> DatasetPreview:
    """Preview the first rows as display text, with null for missing values.

    Cells are limited to 200 characters. Truncation is reported.
    This previews parsed data and is not a lossless CSV export.
    """
    try:
        frame = get_store().load_dataframe(dataset_id)
    except DatasetNotFoundError as exc:
        raise ToolError(
            "Dataset was not found. Use list_datasets to find available IDs."
        ) from exc

    return preview_dataframe(frame, limit=limit)


if __name__ == "__main__":
    mcp.run(transport="stdio")