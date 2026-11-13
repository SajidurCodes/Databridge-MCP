"""HTTP column summaries and expected error responses."""

import pytest
from fastapi.testclient import TestClient

from api import create_app


@pytest.fixture
def summary_client(tmp_path):
    with TestClient(create_app(tmp_path / "datasets.sqlite3")) as client:
        response = client.post(
            "/datasets",
            files={
                "file": (
                    "summary.csv",
                    b"home city,age\nDhaka,20\nDhaka,30\nSylhet,\n",
                    "text/csv",
                )
            },
        )
        assert response.status_code == 201
        yield client, response.json()["dataset_id"]


def test_numeric_summary(summary_client):
    client, dataset_id = summary_client

    response = client.get(
        f"/datasets/{dataset_id}/summary",
        params={"column": "age", "mode": "numeric"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["mode"] == "numeric"
    assert body["summary"]["mean"] == 25
    assert body["summary"]["median"] == 25
    assert body["summary"]["finite_count"] == 2
    assert body["summary"]["missing_count"] == 1


def test_categorical_summary_with_spaced_column_name(summary_client):
    client, dataset_id = summary_client

    response = client.get(
        f"/datasets/{dataset_id}/summary",
        params={
            "column": "home city",
            "mode": "categorical",
            "top_k": 1,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["mode"] == "categorical"
    summary = body["summary"]
    assert summary["top_values"][0]["value"] == "Dhaka"
    assert summary["top_values"][0]["count"] == 2
    assert summary["top_values"][0]["percent_of_nonmissing"] == pytest.approx(
        200 / 3
    )
    assert summary["other_count"] == 1


@pytest.mark.parametrize(
    ("column", "message"),
    [
        ("unknown", "not found"),
        ("home city", "real numeric"),
    ],
)
def test_invalid_column_analysis_returns_400(
    summary_client, column, message
):
    client, dataset_id = summary_client

    response = client.get(
        f"/datasets/{dataset_id}/summary",
        params={"column": column, "mode": "numeric"},
    )

    assert response.status_code == 400
    assert message in response.json()["detail"]


def test_unknown_dataset_returns_404(summary_client):
    client, _ = summary_client

    response = client.get(
        f"/datasets/{'0' * 32}/summary",
        params={"column": "age", "mode": "numeric"},
    )

    assert response.status_code == 404


@pytest.mark.parametrize(
    "params",
    [
        {"column": "age", "mode": "execute_python"},
        {"column": "home city", "mode": "categorical", "top_k": 21},
        {"column": "", "mode": "numeric"},
    ],
)
def test_invalid_summary_parameters_return_422(summary_client, params):
    client, dataset_id = summary_client

    response = client.get(
        f"/datasets/{dataset_id}/summary",
        params=params,
    )

    assert response.status_code == 422