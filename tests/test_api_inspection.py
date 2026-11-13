"""HTTP dataset discovery, profiling, and error behavior."""

import pytest
from fastapi.testclient import TestClient

from api import create_app


@pytest.fixture
def client(tmp_path):
    with TestClient(create_app(tmp_path / "datasets.sqlite3")) as test_client:
        yield test_client


def test_empty_dataset_listing(client):
    response = client.get("/datasets")

    assert response.status_code == 200
    assert response.json() == []


def test_upload_list_and_profile_workflow(client):
    uploaded = client.post(
        "/datasets",
        files={
            "file": (
                "people.csv",
                b"name,age\nNila,24\nNila,24\nRafi,\n",
                "text/csv",
            )
        },
    )
    assert uploaded.status_code == 201
    info = uploaded.json()

    listing = client.get("/datasets")
    assert listing.status_code == 200
    assert listing.json() == [info]

    response = client.get(f"/datasets/{info['dataset_id']}/profile")
    assert response.status_code == 200

    profile = response.json()
    assert profile["row_count"] == 3
    assert profile["column_count"] == 2
    assert profile["duplicate_row_count"] == 1

    columns = {column["name"]: column for column in profile["columns"]}
    assert columns["age"]["missing_count"] == 1
    assert columns["age"]["missing_percent"] == pytest.approx(100 / 3)


def test_listing_limit_returns_newest_dataset(client):
    for filename in ("first.csv", "second.csv"):
        response = client.post(
            "/datasets",
            files={"file": (filename, b"x\n1\n", "text/csv")},
        )
        assert response.status_code == 201

    response = client.get("/datasets", params={"limit": 1})

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["filename"] == "second.csv"


@pytest.mark.parametrize("limit", [0, 101])
def test_invalid_listing_limit(client, limit):
    response = client.get("/datasets", params={"limit": limit})

    assert response.status_code == 422


def test_unknown_dataset_returns_404(client):
    response = client.get(f"/datasets/{'0' * 32}/profile")

    assert response.status_code == 404
    assert response.json()["detail"] == "Dataset was not found."


def test_malformed_dataset_id_returns_422(client):
    response = client.get("/datasets/not-an-id/profile")

    assert response.status_code == 422