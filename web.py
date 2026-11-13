"""Serve the inspection interface alongside the existing API."""

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse

from api import create_app


PAGE_PATH = Path(__file__).resolve().parent / "static" / "index.html"


def create_web_app(database_path: Path | None = None) -> FastAPI:
    app = create_app(database_path)

    @app.get("/", response_class=FileResponse, include_in_schema=False)
    def home() -> FileResponse:
        return FileResponse(PAGE_PATH, media_type="text/html")

    return app