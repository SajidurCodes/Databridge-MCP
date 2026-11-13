"""HTTP upload behavior tested against an isolated database."""

import pytest
from fastapi.testclient import TestClient

import api
from databridge.storage import DatasetStore


@pytest.fixture
def upload_client(tmp_path):
    database_path = tmp_path / "datasets.sqlite3"
    app = api.create_app(database_path)

    with TestClient(app) as client:
        yield client, DatasetStore(database_path)


def test_upload_persists_dataset(upload_client):
    client, store = upload_client
    content = b"name,age\nAmina,20\nRafi,\n"

    response = client.post(
        "/datasets",
        files={"file": ("people.csv", content, "text/csv")},
    )

    assert response.status_code == 201
    result = response.json()
    assert result["filename"] == "people.csv"
    assert result["row_count"] == 2
    assert result["column_count"] == 2
    assert result["size_bytes"] == len(content)

    frame = store.load_dataframe(result["dataset_id"])
    assert frame.loc[0, "name"] == "Amina"
    assert frame["age"].isna().sum() == 1


@pytest.mark.parametrize(
    ("filename", "content", "message"),
    [
        ("empty.csv", b"", "empty"),
        ("broken.csv", b"a,b\n1,2,3\n", "expected 2"),
        ("../people.csv", b"name\nAmina\n", "Filename"),
    ],
)
def test_invalid_upload_is_not_stored(
    upload_client, filename, content, message
):
    client, store = upload_client

    response = client.post(
        "/datasets",
        files={"file": (filename, content, "text/csv")},
    )

    assert response.status_code == 400
    assert message in response.json()["detail"]
    assert store.list_datasets() == []


def test_upload_size_boundary(upload_client, monkeypatch):
    client, store = upload_client
    content = b"x\n1\n"
    monkeypatch.setattr(api, "MAX_BYTES", len(content))

    accepted = client.post(
        "/datasets",
        files={"file": ("exact.csv", content, "text/csv")},
    )
    assert accepted.status_code == 201

    rejected = client.post(
        "/datasets",
        files={"file": ("over.csv", content + b"2", "text/csv")},
    )
    assert rejected.status_code == 413

    datasets = store.list_datasets()
    assert len(datasets) == 1
    assert datasets[0].filename == "exact.csv"


def test_missing_upload_returns_validation_error(upload_client):
    client, store = upload_client

    response = client.post("/datasets")

    assert response.status_code == 422
    assert store.list_datasets() == []