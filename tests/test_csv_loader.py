"""CSV parsing policies and resource-limit checks."""

import pytest

from databridge import csv_loader
from databridge.csv_loader import CsvValidationError, load_csv_bytes
from databridge.profiling import profile_dataframe


def test_csv_loads_and_profiles_with_explicit_missing_policy():
    content = (
        b"\xef\xbb\xbfname,age,note\r\n"
        b'Amina,20,"hello, world"\r\n'
        b"Rafi,,NA\r\n"
        b"Mina,30,NULL\r\n"
    )

    frame = load_csv_bytes(content)
    profile = profile_dataframe(frame)

    assert frame.shape == (3, 3)
    assert frame.loc[0, "note"] == "hello, world"
    assert frame.loc[1, "note"] == "NA"
    assert frame.loc[2, "note"] == "NULL"
    assert frame.loc[0, "age"] == 20
    assert profile.columns[1].missing_count == 1
    assert profile.columns[2].missing_count == 0


def test_header_only_csv_is_accepted():
    frame = load_csv_bytes(b"name,age\n")

    assert list(frame.columns) == ["name", "age"]
    assert len(frame) == 0


@pytest.mark.parametrize(
    ("content", "message"),
    [
        (b"", "empty"),
        (b"name\n\xff", "UTF-8"),
        (b"name\nab\x00cd", "null bytes"),
        (b"name,name\nA,B", "unique"),
        (b"name, \nA,B", "nonblank"),
        (b"name,age\nA", "expected 2"),
        (b"name,age\nA,20,extra", "expected 2"),
        (b'name\n"unfinished', "syntax"),
    ],
)
def test_invalid_csv_is_rejected(content, message):
    with pytest.raises(CsvValidationError, match=message):
        load_csv_bytes(content)


@pytest.mark.parametrize(
    ("limit_name", "content"),
    [
        ("MAX_BYTES", b"x\n1\n"),
        ("MAX_ROWS", b"x\n1\n2\n"),
        ("MAX_COLUMNS", b"x,y\n1,2\n"),
    ],
)
def test_limits_accept_boundary_and_reject_overflow(
    monkeypatch, limit_name, content
):
    boundary = len(content) if limit_name == "MAX_BYTES" else 2

    monkeypatch.setattr(csv_loader, limit_name, boundary)
    load_csv_bytes(content)

    monkeypatch.setattr(csv_loader, limit_name, boundary - 1)
    with pytest.raises(CsvValidationError, match="limit"):
        load_csv_bytes(content)