"""Local dataset storage shared by MCP and FastAPI."""

import re
import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import pandas as pd
from pydantic import BaseModel

from databridge.csv_loader import load_csv_bytes


class DatasetNotFoundError(LookupError):
    """No stored dataset matches the requested ID."""


class DatasetInfo(BaseModel):
    dataset_id: str
    filename: str
    row_count: int
    column_count: int
    size_bytes: int
    created_at: str


class DatasetStore:
    """Store validated CSV bytes with generated, opaque identifiers."""

    def __init__(self, database_path: Path) -> None:
        self.database_path = database_path.resolve()
        self.database_path.parent.mkdir(parents=True, exist_ok=True)

        with closing(self._connect()) as connection:
            with connection:
                connection.execute(
                    """
                    CREATE TABLE IF NOT EXISTS datasets (
                        dataset_id TEXT PRIMARY KEY,
                        filename TEXT NOT NULL,
                        row_count INTEGER NOT NULL,
                        column_count INTEGER NOT NULL,
                        size_bytes INTEGER NOT NULL,
                        created_at TEXT NOT NULL,
                        content BLOB NOT NULL
                    )
                    """
                )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path, timeout=10)
        connection.row_factory = sqlite3.Row
        return connection

    @staticmethod
    def _validate_id(dataset_id: str) -> None:
        if re.fullmatch(r"[0-9a-f]{32}", dataset_id) is None:
            raise ValueError("Dataset ID must contain 32 lowercase hex characters.")

    def add_csv(self, filename: str, content: bytes) -> DatasetInfo:
        """Validate first, then atomically store content and metadata."""
        if (
            not filename.strip()
            or len(filename) > 255
            or any(character in filename for character in ("/", "\\", "\x00"))
        ):
            raise ValueError("Filename must be a nonblank name without a path.")

        frame = load_csv_bytes(content)
        info = DatasetInfo(
            dataset_id=uuid4().hex,
            filename=filename,
            row_count=len(frame),
            column_count=frame.shape[1],
            size_bytes=len(content),
            created_at=datetime.now(timezone.utc).isoformat(),
        )

        with closing(self._connect()) as connection:
            with connection:
                connection.execute(
                    """
                    INSERT INTO datasets (
                        dataset_id, filename, row_count, column_count,
                        size_bytes, created_at, content
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        info.dataset_id,
                        info.filename,
                        info.row_count,
                        info.column_count,
                        info.size_bytes,
                        info.created_at,
                        content,
                    ),
                )

        return info

    def load_dataframe(self, dataset_id: str) -> pd.DataFrame:
        """Load a dataset by ID; reject malformed or unknown IDs."""
        self._validate_id(dataset_id)

        with closing(self._connect()) as connection:
            row = connection.execute(
                "SELECT content FROM datasets WHERE dataset_id = ?",
                (dataset_id,),
            ).fetchone()

        if row is None:
            raise DatasetNotFoundError("Dataset was not found.")

        return load_csv_bytes(bytes(row["content"]))

    def list_datasets(self, limit: int = 20) -> list[DatasetInfo]:
        """Return at most 100 datasets, newest first."""
        if not 1 <= limit <= 100:
            raise ValueError("Limit must be between 1 and 100.")

        with closing(self._connect()) as connection:
            rows = connection.execute(
                """
                SELECT dataset_id, filename, row_count, column_count,
                       size_bytes, created_at
                FROM datasets
                ORDER BY rowid DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()

        return [DatasetInfo(**dict(row)) for row in rows]