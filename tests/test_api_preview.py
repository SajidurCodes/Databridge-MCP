"""HTTP preview serialization, limits, and error handling."""

import pytest
from fastapi.testclient import TestClient

from api import create_app


@pytest.fixture
def preview_client(tmp_path):
    with TestClient(create_app(tmp_path / "datasets.sqlite3")) as client:
        response = client.post(
            "/datasets",
            files={
                "file": (
                    "preview.csv",
                    b"name,age\nNila,24\nRafi,\nMina,30\n",
                    "text/csv",
                )
            },
        )
        assert response.status_code == 201
        yield client, response.json()["dataset_id"]


def test_preview_returns_bounded_rows_and_json_null(preview_client):
    client, dataset_id = preview_client

    response = client.get(
        f"/datasets/{dataset_id}/preview",
        params={"limit": 2},
    )

    assert response.status_code == 200
    assert response.json() == {
        "columns": ["name", "age"],
        "rows": [["Nila", "24"], ["Rafi", None]],
        "total_rows": 3,
        "returned_rows": 2,
        "has_more_rows": True,
        "truncated_cells": 0,
    }


def test_preview_uses_default_limit(preview_client):
    client, dataset_id = preview_client

    response = client.get(f"/datasets/{dataset_id}/preview")

    assert response.status_code == 200
    assert response.json()["returned_rows"] == 3
    assert response.json()["has_more_rows"] is False


@pytest.mark.parametrize("limit", [0, 51])
def test_preview_rejects_invalid_limits(preview_client, limit):
    client, dataset_id = preview_client

    response = client.get(
        f"/datasets/{dataset_id}/preview",
        params={"limit": limit},
    )

    assert response.status_code == 422


def test_preview_unknown_dataset_returns_404(preview_client):
    client, _ = preview_client

    response = client.get(f"/datasets/{'0' * 32}/preview")

    assert response.status_code == 404
    assert response.json()["detail"] == "Dataset was not found."


def test_preview_malformed_id_returns_422(preview_client):
    client, _ = preview_client

    response = client.get("/datasets/not-an-id/preview")

    assert response.status_code == 422