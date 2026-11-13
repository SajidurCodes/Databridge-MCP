"""Preview ordering, missing values, limits, and truncation."""

import json

import pandas as pd
import pytest

from databridge.csv_loader import load_csv_bytes
from databridge.preview import preview_dataframe


def test_preview_preserves_order_and_distinguishes_missing_values():
    frame = load_csv_bytes(b"name,age\nNA,24\nRafi,\n")
    original = frame.copy(deep=True)

    result = preview_dataframe(frame)

    assert result.columns == ["name", "age"]
    assert result.rows == [["NA", "24"], ["Rafi", None]]
    assert result.total_rows == 2
    assert result.returned_rows == 2
    assert result.has_more_rows is False
    assert result.truncated_cells == 0
    assert json.loads(result.model_dump_json())["rows"][1][1] is None
    pd.testing.assert_frame_equal(frame, original)


def test_preview_limits_rows():
    frame = pd.DataFrame({"value": range(8)})

    result = preview_dataframe(frame, limit=3)

    assert result.rows == [["0"], ["1"], ["2"]]
    assert result.total_rows == 8
    assert result.returned_rows == 3
    assert result.has_more_rows is True


def test_preview_accepts_maximum_row_limit():
    frame = pd.DataFrame({"value": range(51)})

    result = preview_dataframe(frame, limit=50)

    assert result.returned_rows == 50
    assert result.has_more_rows is True


def test_header_only_preview():
    frame = load_csv_bytes(b"name,age\n")

    result = preview_dataframe(frame)

    assert result.columns == ["name", "age"]
    assert result.rows == []
    assert result.total_rows == 0
    assert result.returned_rows == 0
    assert result.has_more_rows is False


def test_long_cells_are_shortened_without_changing_source():
    frame = pd.DataFrame({"text": ["a" * 200, "b" * 201]})

    result = preview_dataframe(frame)

    assert result.rows[0][0] == "a" * 200
    assert result.rows[1][0] == "b" * 199 + "…"
    assert result.truncated_cells == 1
    assert frame.loc[1, "text"] == "b" * 201


@pytest.mark.parametrize("limit", [0, 51, True, 1.5])
def test_invalid_preview_limits(limit):
    frame = pd.DataFrame({"value": [1]})

    with pytest.raises(ValueError, match="limit"):
        preview_dataframe(frame, limit=limit)