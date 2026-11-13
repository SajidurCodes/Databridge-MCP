"""Tests with independently calculated profiling expectations."""

import pandas as pd
import pytest

from databridge.profiling import profile_dataframe


def test_known_counts_and_input_unchanged():
    frame = pd.DataFrame(
        {
            "name": ["Amina", "Amina", "Rafi", "Mina"],
            "age": pd.Series([20, 20, None, None], dtype="Int64"),
        }
    )
    original = frame.copy(deep=True)

    result = profile_dataframe(frame)
    columns = {column.name: column for column in result.columns}

    assert result.row_count == 4
    assert result.column_count == 2
    assert result.duplicate_row_count == 1
    assert [column.name for column in result.columns] == ["name", "age"]
    assert columns["name"].missing_count == 0
    assert columns["age"].dtype == "Int64"
    assert columns["age"].missing_count == 2
    assert columns["age"].missing_percent == pytest.approx(50.0)
    pd.testing.assert_frame_equal(frame, original)


def test_header_only_table_has_zero_missing_percentage():
    frame = pd.DataFrame({"age": pd.Series([], dtype="Int64")})

    result = profile_dataframe(frame)

    assert result.row_count == 0
    assert result.column_count == 1
    assert result.duplicate_row_count == 0
    assert result.columns[0].missing_count == 0
    assert result.columns[0].missing_percent == 0.0


def test_empty_string_is_not_a_missing_value():
    frame = pd.DataFrame({"label": ["", None, "valid"]})

    result = profile_dataframe(frame)

    assert result.columns[0].missing_count == 1
    assert result.columns[0].missing_percent == pytest.approx(100 / 3)


@pytest.mark.parametrize(
    ("frame", "message"),
    [
        (pd.DataFrame(), "at least one column"),
        (pd.DataFrame([[1, 2]], columns=["x", "x"]), "unique"),
        (pd.DataFrame([[1]], columns=[" "]), "nonblank strings"),
        (pd.DataFrame([[1]], columns=[123]), "nonblank strings"),
    ],
)
def test_invalid_columns_are_rejected(frame, message):
    with pytest.raises(ValueError, match=message):
        profile_dataframe(frame)