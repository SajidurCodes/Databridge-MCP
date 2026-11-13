"""Shared entry point for column summaries."""

from typing import Literal

import pandas as pd
from pydantic import BaseModel

from databridge.category_summary import (
    CategoricalColumnSummary,
    summarize_categorical_column,
)
from databridge.column_summary import (
    ColumnSummaryError,
    NumericColumnSummary,
    summarize_numeric_column,
)


SummaryMode = Literal["numeric", "categorical"]


class ColumnSummaryResult(BaseModel):
    mode: SummaryMode
    summary: NumericColumnSummary | CategoricalColumnSummary


def summarize_column_dataframe(
    frame: pd.DataFrame,
    column: str,
    mode: SummaryMode,
    top_k: int = 5,
) -> ColumnSummaryResult:
    """Select a predefined summary operation."""
    if mode == "numeric":
        summary = summarize_numeric_column(frame, column)
    elif mode == "categorical":
        summary = summarize_categorical_column(frame, column, top_k=top_k)
    else:
        raise ColumnSummaryError("Mode must be numeric or categorical.")

    return ColumnSummaryResult(mode=mode, summary=summary)