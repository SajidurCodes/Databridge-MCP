"""Bounded CSV parsing for locally uploaded datasets."""

import csv
from io import StringIO

import pandas as pd


MAX_BYTES = 5 * 1024 * 1024
MAX_ROWS = 10_000
MAX_COLUMNS = 100


class CsvValidationError(ValueError):
    """The uploaded content does not meet our CSV requirements."""


def load_csv_bytes(content: bytes) -> pd.DataFrame:
    """Validate UTF-8 CSV bytes and return a typed DataFrame."""
    if len(content) > MAX_BYTES:
        raise CsvValidationError("CSV exceeds the 5 MiB size limit.")

    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise CsvValidationError("CSV must use UTF-8 encoding.") from exc

    if not text.strip():
        raise CsvValidationError("CSV is empty.")

    if "\x00" in text:
        raise CsvValidationError("CSV must not contain null bytes.")

    # Validate before pandas can rename headers or fill short records.
    try:
        reader = csv.reader(StringIO(text, newline=""), strict=True)
        header = next(reader)

        if not header or any(not name.strip() for name in header):
            raise CsvValidationError("Column names must be nonblank.")

        if len(set(header)) != len(header):
            raise CsvValidationError("Column names must be unique.")

        if len(header) > MAX_COLUMNS:
            raise CsvValidationError("CSV exceeds the column limit.")

        for row_number, row in enumerate(reader, start=1):
            if row_number > MAX_ROWS:
                raise CsvValidationError("CSV exceeds the row limit.")
            if len(row) != len(header):
                raise CsvValidationError(
                    f"Data record {row_number} has {len(row)} fields; "
                    f"expected {len(header)}."
                )
    except (csv.Error, StopIteration) as exc:
        raise CsvValidationError("CSV syntax is invalid.") from exc

    try:
        return pd.read_csv(
            StringIO(text),
            sep=",",
            header=0,
            index_col=False,
            keep_default_na=False,
            na_values=[""],
            skip_blank_lines=False,
            dtype_backend="numpy_nullable",
        )
    except (pd.errors.ParserError, pd.errors.EmptyDataError, ValueError) as exc:
        raise CsvValidationError("CSV could not be parsed.") from exc