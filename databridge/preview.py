"""Bounded display previews for validated CSV datasets."""

import pandas as pd
from pydantic import BaseModel, Field


MAX_PREVIEW_ROWS = 50
MAX_CELL_CHARACTERS = 200


class DatasetPreview(BaseModel):
    columns: list[str]
    rows: list[list[str | None]]
    total_rows: int = Field(ge=0)
    returned_rows: int = Field(ge=0, le=MAX_PREVIEW_ROWS)
    has_more_rows: bool
    truncated_cells: int = Field(ge=0)


def preview_dataframe(
    frame: pd.DataFrame,
    limit: int = 5,
) -> DatasetPreview:
    """Preview a validated, scalar-valued CSV table as display text."""
    if isinstance(limit, bool) or not isinstance(limit, int):
        raise ValueError("Preview limit must be an integer.")
    if not 1 <= limit <= MAX_PREVIEW_ROWS:
        raise ValueError("Preview limit must be between 1 and 50.")

    rows: list[list[str | None]] = []
    truncated_cells = 0

    for values in frame.head(limit).itertuples(index=False, name=None):
        row: list[str | None] = []

        for value in values:
            if pd.isna(value):
                row.append(None)
                continue

            text = str(value)
            if len(text) > MAX_CELL_CHARACTERS:
                text = text[: MAX_CELL_CHARACTERS - 1] + "…"
                truncated_cells += 1

            row.append(text)

        rows.append(row)

    return DatasetPreview(
        columns=list(frame.columns),
        rows=rows,
        total_rows=len(frame),
        returned_rows=len(rows),
        has_more_rows=len(frame) > len(rows),
        truncated_cells=truncated_cells,
    )