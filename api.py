"""HTTP interface for uploading and inspecting datasets."""

from pathlib import Path
from typing import Annotated

from fastapi import (
    FastAPI,
    File,
    HTTPException,
    Path as PathParameter,
    Query,
    UploadFile,
)

from databridge.csv_loader import MAX_BYTES
from databridge.preview import DatasetPreview, preview_dataframe
from databridge.profiling import DatasetProfile, profile_dataframe
from databridge.storage import (
    DatasetInfo,
    DatasetNotFoundError,
    DatasetStore,
)


DEFAULT_DATABASE_PATH = (
    Path(__file__).resolve().parent / "data" / "datasets.sqlite3"
)

DatasetId = Annotated[
    str,
    PathParameter(
        pattern=r"^[0-9a-f]{32}$",
        description="Dataset ID returned by upload or listing.",
    ),
]


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
            content = file.file.read(MAX_BYTES + 1)

            if len(content) > MAX_BYTES:
                raise HTTPException(
                    status_code=413,
                    detail="CSV exceeds the 5 MiB size limit.",
                )

            try:
                return store.add_csv(file.filename or "", content)
            except ValueError as exc:
                raise HTTPException(status_code=400, detail=str(exc)) from exc
        finally:
            file.file.close()

    @app.get("/datasets", response_model=list[DatasetInfo])
    def list_datasets(
        limit: Annotated[
            int,
            Query(ge=1, le=100, description="Maximum datasets to return."),
        ] = 20,
    ) -> list[DatasetInfo]:
        """List stored datasets, newest first."""
        return store.list_datasets(limit=limit)

    @app.get(
        "/datasets/{dataset_id}/profile",
        response_model=DatasetProfile,
    )
    def get_dataset_profile(dataset_id: DatasetId) -> DatasetProfile:
        """Profile one stored dataset."""
        try:
            frame = store.load_dataframe(dataset_id)
        except DatasetNotFoundError as exc:
            raise HTTPException(
                status_code=404,
                detail="Dataset was not found.",
            ) from exc

        return profile_dataframe(frame)

    @app.get(
        "/datasets/{dataset_id}/preview",
        response_model=DatasetPreview,
    )
    def get_dataset_preview(
        dataset_id: DatasetId,
        limit: Annotated[
            int,
            Query(ge=1, le=50, description="Maximum preview rows to return."),
        ] = 5,
    ) -> DatasetPreview:
        """Preview parsed data as text, with null for missing values.

        Cells are limited to 200 characters. Truncation is reported.
        This is not a lossless CSV export.
        """
        try:
            frame = store.load_dataframe(dataset_id)
        except DatasetNotFoundError as exc:
            raise HTTPException(
                status_code=404,
                detail="Dataset was not found.",
            ) from exc

        return preview_dataframe(frame, limit=limit)

    return app