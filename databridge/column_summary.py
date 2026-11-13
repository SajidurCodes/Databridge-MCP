"""Numeric summaries for validated CSV datasets."""

import math
import statistics

import pandas as pd
from pandas.api.types import (
    is_bool_dtype,
    is_complex_dtype,
    is_numeric_dtype,
)
from pydantic import BaseModel, ConfigDict, Field


class ColumnSummaryError(ValueError):
    """The requested column cannot be summarized numerically."""


class NumericColumnSummary(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False)

    column: str
    dtype: str
    total_count: int = Field(ge=0)
    missing_count: int = Field(ge=0)
    infinite_count: int = Field(ge=0)
    finite_count: int = Field(ge=0)
    minimum: float | None
    maximum: float | None
    mean: float | None
    median: float | None


def summarize_numeric_column(
    frame: pd.DataFrame,
    column: str,
) -> NumericColumnSummary:
    """Calculate statistics from finite values in one numeric column."""
    if column not in frame.columns:
        raise ColumnSummaryError("Column was not found.")

    series = frame[column]
    if (
        not is_numeric_dtype(series.dtype)
        or is_bool_dtype(series.dtype)
        or is_complex_dtype(series.dtype)
    ):
        raise ColumnSummaryError("Column must have a real numeric dtype.")

    missing_count = int(series.isna().sum())
    values = [float(value) for value in series.dropna()]
    finite_values = [value for value in values if math.isfinite(value)]
    infinite_count = sum(math.isinf(value) for value in values)

    minimum = maximum = average = median = None

    if finite_values:
        ordered = sorted(finite_values)
        minimum = ordered[0]
        maximum = ordered[-1]
        average = statistics.mean(ordered)

        middle = len(ordered) // 2
        if len(ordered) % 2:
            median = ordered[middle]
        else:
            # Avoid overflow from directly adding two large middle values.
            median = statistics.mean(ordered[middle - 1 : middle + 1])

    return NumericColumnSummary(
        column=column,
        dtype=str(series.dtype),
        total_count=len(series),
        missing_count=missing_count,
        infinite_count=infinite_count,
        finite_count=len(finite_values),
        minimum=minimum,
        maximum=maximum,
        mean=average,
        median=median,
    )