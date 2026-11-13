"""HTTP interface for uploading datasets."""

from pathlib import Path
from typing import Annotated

from fastapi import FastAPI, File, HTTPException, UploadFile

from databridge.csv_loader import MAX_BYTES
from databridge.storage import DatasetInfo, DatasetStore


DEFAULT_DATABASE_PATH = (
    Path(__file__).resolve().parent / "data" / "datasets.sqlite3"
)


def create_app(database_path: Path | None = None) -> FastAPI:
    """Create an application using the selected local database."""
    store = DatasetStore(
        database_path if database_path is not None else DEFAULT_DATABASE_PATH
    )
    app = FastAPI(
        title="DataBridge API",
        version="0.1.0",
        description="Local CSV validation and inspection.",
    )

    @app.post(
        "/datasets",
        response_model=DatasetInfo,
        status_code=201,
    )
    def upload_dataset(
        file: Annotated[
            UploadFile,
            File(description="UTF-8, comma-separated CSV with a header."),
        ],
    ) -> DatasetInfo:
        """Validate and store one CSV, returning its generated dataset ID."""
        try:
            # Read one extra byte to detect an oversized file.
            content = file.file.read(MAX_BYTES + 1)

            if len(content) > MAX_BYTES:
                raise HTTPException(
                    status_code=413,
                    detail="CSV exceeds the 5 MiB size limit.",
                )

            try:
                return store.add_csv(file.filename or "", content)
            except ValueError as exc:
                # CSV and filename validation failures are client errors.
                raise HTTPException(status_code=400, detail=str(exc)) from exc
        finally:
            file.file.close()

    return app