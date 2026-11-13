"""Bounded category frequencies for validated CSV datasets."""

import pandas as pd
from pydantic import BaseModel, Field

from databridge.column_summary import ColumnSummaryError


MAX_CATEGORIES = 20
MAX_LABEL_CHARACTERS = 200


class CategoryFrequency(BaseModel):
    value: str
    count: int = Field(ge=1)
    percent_of_nonmissing: float = Field(ge=0, le=100)
    label_truncated: bool


class CategoricalColumnSummary(BaseModel):
    column: str
    dtype: str
    total_count: int = Field(ge=0)
    missing_count: int = Field(ge=0)
    nonmissing_count: int = Field(ge=0)
    unique_count: int = Field(ge=0)
    top_values: list[CategoryFrequency]
    omitted_category_count: int = Field(ge=0)
    other_count: int = Field(ge=0)


def summarize_categorical_column(
    frame: pd.DataFrame,
    column: str,
    top_k: int = 5,
) -> CategoricalColumnSummary:
    """Count exact values; shorten labels only after counting."""
    if isinstance(top_k, bool) or not isinstance(top_k, int):
        raise ColumnSummaryError("top_k must be an integer.")
    if not 1 <= top_k <= MAX_CATEGORIES:
        raise ColumnSummaryError("top_k must be between 1 and 20.")
    if column not in frame.columns:
        raise ColumnSummaryError("Column was not found.")

    series = frame[column]
    missing_count = int(series.isna().sum())
    nonmissing_count = len(series) - missing_count

    counts = series.value_counts(dropna=True, sort=False)
    ranked = sorted(
        (
            (str(value), int(count))
            for value, count in counts.items()
            if count > 0
        ),
        key=lambda item: (-item[1], item[0]),
    )

    top_values = []
    for label, count in ranked[:top_k]:
        truncated = len(label) > MAX_LABEL_CHARACTERS
        display_label = (
            label[: MAX_LABEL_CHARACTERS - 1] + "…"
            if truncated
            else label
        )
        top_values.append(
            CategoryFrequency(
                value=display_label,
                count=count,
                percent_of_nonmissing=100.0 * count / nonmissing_count,
                label_truncated=truncated,
            )
        )

    return CategoricalColumnSummary(
        column=column,
        dtype=str(series.dtype),
        total_count=len(series),
        missing_count=missing_count,
        nonmissing_count=nonmissing_count,
        unique_count=len(ranked),
        top_values=top_values,
        omitted_category_count=max(0, len(ranked) - top_k),
        other_count=sum(count for _, count in ranked[top_k:]),
    )