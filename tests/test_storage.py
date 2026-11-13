"""Persistence, validation, and dataset isolation checks."""

import pytest

from databridge.csv_loader import CsvValidationError
from databridge.storage import DatasetNotFoundError, DatasetStore


@pytest.fixture
def store(tmp_path):
    return DatasetStore(tmp_path / "data" / "datasets.sqlite3")


def test_dataset_survives_store_recreation(tmp_path):
    database_path = tmp_path / "datasets.sqlite3"
    first_store = DatasetStore(database_path)
    content = b"name,age\nAmina,20\nRafi,\n"

    info = first_store.add_csv("people.csv", content)

    second_store = DatasetStore(database_path)
    frame = second_store.load_dataframe(info.dataset_id)

    assert len(info.dataset_id) == 32
    assert info.row_count == 2
    assert info.column_count == 2
    assert info.size_bytes == len(content)
    assert frame.loc[0, "name"] == "Amina"
    assert frame["age"].isna().sum() == 1
    assert second_store.list_datasets() == [info]


def test_same_filename_does_not_overwrite_dataset(store):
    first = store.add_csv("sample.csv", b"value\n10\n")
    second = store.add_csv("sample.csv", b"value\n20\n")

    assert first.dataset_id != second.dataset_id
    assert store.load_dataframe(first.dataset_id).iloc[0, 0] == 10
    assert store.load_dataframe(second.dataset_id).iloc[0, 0] == 20
    assert store.list_datasets(limit=1) == [second]


def test_invalid_csv_is_not_stored(store):
    with pytest.raises(CsvValidationError):
        store.add_csv("broken.csv", b"a,b\n1,2,3\n")

    assert store.list_datasets() == []


def test_unknown_dataset_is_not_found(store):
    with pytest.raises(DatasetNotFoundError):
        store.load_dataframe("0" * 32)


@pytest.mark.parametrize("dataset_id", ["../secret", "", "g" * 32])
def test_malformed_ids_are_rejected(store, dataset_id):
    with pytest.raises(ValueError, match="Dataset ID"):
        store.load_dataframe(dataset_id)


@pytest.mark.parametrize("filename", ["../sample.csv", r"C:\sample.csv", " "])
def test_invalid_filenames_are_rejected(store, filename):
    with pytest.raises(ValueError, match="Filename"):
        store.add_csv(filename, b"value\n1\n")

    assert store.list_datasets() == []


@pytest.mark.parametrize("limit", [0, 101])
def test_invalid_listing_limits_are_rejected(store, limit):
    with pytest.raises(ValueError, match="Limit"):
        store.list_datasets(limit=limit)