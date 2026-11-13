"""Dataset profiling shared by the MCP and HTTP adapters."""

import pandas as pd
from pydantic import BaseModel, Field


class ColumnProfile(BaseModel):
    name: str
    dtype: str
    missing_count: int = Field(ge=0)
    missing_percent: float = Field(ge=0, le=100)


class DatasetProfile(BaseModel):
    row_count: int = Field(ge=0)
    column_count: int = Field(ge=1)
    duplicate_row_count: int = Field(ge=0)
    columns: list[ColumnProfile]


def profile_dataframe(frame: pd.DataFrame) -> DatasetProfile:
    """Profile a scalar-valued table without modifying it.

    Duplicate rows exclude the first occurrence.
    Missing percentages are zero when the table has no rows.
    Column names must be unique, nonblank strings.
    """
    if frame.shape[1] == 0:
        raise ValueError("Dataset must contain at least one column.")

    if not frame.columns.is_unique:
        raise ValueError("Column names must be unique.")

    if any(
        not isinstance(name, str) or not name.strip()
        for name in frame.columns
    ):
        raise ValueError("Column names must be nonblank strings.")

    row_count = len(frame)
    missing_counts = frame.isna().sum()

    columns = []
    for name in frame.columns:
        missing_count = int(missing_counts[name])
        columns.append(
            ColumnProfile(
                name=name,
                dtype=str(frame[name].dtype),
                missing_count=missing_count,
                missing_percent=(
                    100.0 * missing_count / row_count
                    if row_count
                    else 0.0
                ),
            )
        )

    return DatasetProfile(
        row_count=row_count,
        column_count=frame.shape[1],
        duplicate_row_count=int(frame.duplicated().sum()),
        columns=columns,
    )