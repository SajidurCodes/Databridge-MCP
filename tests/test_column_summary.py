"""Known numeric results and edge cases."""

import json

import pandas as pd
import pytest

from databridge.column_summary import (
    ColumnSummaryError,
    summarize_numeric_column,
)


def test_known_statistics_and_input_unchanged():
    frame = pd.DataFrame(
        {"score": pd.Series([10, 20, 30, None], dtype="Int64")}
    )
    original = frame.copy(deep=True)

    result = summarize_numeric_column(frame, "score")

    assert result.total_count == 4
    assert result.missing_count == 1
    assert result.infinite_count == 0
    assert result.finite_count == 3
    assert result.minimum == 10
    assert result.maximum == 30
    assert result.mean == 20
    assert result.median == 20
    pd.testing.assert_frame_equal(frame, original)


def test_infinities_are_counted_and_excluded():
    frame = pd.DataFrame(
        {"score": [2.0, 4.0, float("inf"), float("-inf"), float("nan")]}
    )

    result = summarize_numeric_column(frame, "score")

    assert result.total_count == 5
    assert result.missing_count == 1
    assert result.infinite_count == 2
    assert result.finite_count == 2
    assert result.minimum == 2
    assert result.maximum == 4
    assert result.mean == 3
    assert result.median == 3


@pytest.mark.parametrize(
    "values",
    [
        [],
        [None, None],
        [float("inf"), float("-inf")],
    ],
)
def test_no_finite_values_returns_null_statistics(values):
    frame = pd.DataFrame(
        {"score": pd.Series(values, dtype="Float64")}
    )

    result = summarize_numeric_column(frame, "score")

    assert result.finite_count == 0
    assert (
        result.missing_count + result.infinite_count
        == result.total_count
    )
    assert result.minimum is None
    assert result.maximum is None
    assert result.mean is None
    assert result.median is None
    assert json.loads(result.model_dump_json())["mean"] is None


def test_large_finite_values_do_not_overflow():
    frame = pd.DataFrame({"score": [1e308, 1e308]})

    result = summarize_numeric_column(frame, "score")

    assert result.mean == 1e308
    assert result.median == 1e308


@pytest.mark.parametrize("values", [["10", "20"], [True, False]])
def test_nonnumeric_columns_are_rejected(values):
    frame = pd.DataFrame({"value": values})

    with pytest.raises(ColumnSummaryError, match="real numeric"):
        summarize_numeric_column(frame, "value")


def test_unknown_column_is_rejected():
    frame = pd.DataFrame({"score": [1, 2]})

    with pytest.raises(ColumnSummaryError, match="not found"):
        summarize_numeric_column(frame, "missing")