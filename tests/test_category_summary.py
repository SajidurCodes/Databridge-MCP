"""Category counts, denominator policy, ordering, and bounds."""

import pandas as pd
import pytest

from databridge.category_summary import summarize_categorical_column
from databridge.column_summary import ColumnSummaryError


def test_known_frequencies_and_omitted_counts():
    frame = pd.DataFrame(
        {"city": ["Dhaka", "Dhaka", "Dhaka", "Sylhet", "Khulna", None]}
    )
    original = frame.copy(deep=True)

    result = summarize_categorical_column(frame, "city", top_k=2)

    assert result.total_count == 6
    assert result.missing_count == 1
    assert result.nonmissing_count == 5
    assert result.unique_count == 3
    assert [item.value for item in result.top_values] == ["Dhaka", "Khulna"]
    assert [item.count for item in result.top_values] == [3, 1]
    assert result.top_values[0].percent_of_nonmissing == 60.0
    assert result.top_values[1].percent_of_nonmissing == 20.0
    assert result.omitted_category_count == 1
    assert result.other_count == 1
    pd.testing.assert_frame_equal(frame, original)


@pytest.mark.parametrize("values", [[], [None, None]])
def test_empty_or_all_missing_column(values):
    frame = pd.DataFrame({"city": pd.Series(values, dtype="string")})

    result = summarize_categorical_column(frame, "city")

    assert result.total_count == len(values)
    assert result.missing_count == len(values)
    assert result.nonmissing_count == 0
    assert result.unique_count == 0
    assert result.top_values == []
    assert result.other_count == 0
    assert result.omitted_category_count == 0


def test_frequency_ties_are_alphabetical():
    frame = pd.DataFrame({"label": ["Zebra", "Apple", "Mango"]})

    result = summarize_categorical_column(frame, "label")

    assert [item.value for item in result.top_values] == [
        "Apple", "Mango", "Zebra"
    ]


def test_long_labels_are_counted_before_truncation():
    first = "x" * 200 + "A"
    second = "x" * 200 + "B"
    frame = pd.DataFrame({"label": [first, first, second]})

    result = summarize_categorical_column(frame, "label")

    assert result.unique_count == 2
    assert [item.count for item in result.top_values] == [2, 1]
    assert all(item.label_truncated for item in result.top_values)
    assert all(len(item.value) == 200 for item in result.top_values)
    assert frame.loc[0, "label"] == first


def test_numeric_category_codes_are_supported():
    frame = pd.DataFrame({"code": [2, 1, 2]})

    result = summarize_categorical_column(frame, "code")

    assert [item.value for item in result.top_values] == ["2", "1"]
    assert [item.count for item in result.top_values] == [2, 1]


def test_unknown_column_is_rejected():
    frame = pd.DataFrame({"city": ["Dhaka"]})

    with pytest.raises(ColumnSummaryError, match="not found"):
        summarize_categorical_column(frame, "missing")


@pytest.mark.parametrize("top_k", [0, 21, True, 1.5])
def test_invalid_category_limits(top_k):
    frame = pd.DataFrame({"city": ["Dhaka"]})

    with pytest.raises(ColumnSummaryError, match="top_k"):
        summarize_categorical_column(frame, "city", top_k=top_k)