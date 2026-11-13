"""Reproducible local benchmark with an equivalent row-loop baseline."""

import csv
import gc
import io
import json
import platform
import statistics
import sys
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path
from time import perf_counter
from typing import Callable

import pandas as pd

from databridge.csv_loader import load_csv_bytes
from databridge.profiling import (
    ColumnProfile,
    DatasetProfile,
    profile_dataframe,
)


REPEATS = 7
ROW_COUNTS = (100, 1_000, 10_000)


def make_csv(row_count: int) -> bytes:
    """Generate deterministic data with missing cells and duplicate rows."""
    buffer = io.StringIO(newline="")
    writer = csv.writer(buffer)
    writer.writerow(["city", "age", "score", "group"])

    previous = None
    for index in range(row_count):
        if index > 0 and index % 10 == 0:
            row = previous.copy()
        else:
            row = [
                ["Dhaka", "Sylhet", "Khulna"][index % 3],
                "" if index % 7 == 0 else 18 + index % 60,
                "" if index % 11 == 0 else (index * 13) % 101,
                f"group_{index % 8}",
            ]
        writer.writerow(row)
        previous = row

    return buffer.getvalue().encode("utf-8")


def profile_with_row_loop(frame: pd.DataFrame) -> DatasetProfile:
    """Simple baseline for the same validated scalar-valued input."""
    missing = [0] * frame.shape[1]
    seen = set()
    duplicate_count = 0

    for values in frame.itertuples(index=False, name=None):
        normalized = []
        for index, value in enumerate(values):
            if pd.isna(value):
                missing[index] += 1
                normalized.append(None)
            else:
                normalized.append(value)

        key = tuple(normalized)
        if key in seen:
            duplicate_count += 1
        else:
            seen.add(key)

    row_count = len(frame)
    columns = [
        ColumnProfile(
            name=name,
            dtype=str(frame[name].dtype),
            missing_count=missing[index],
            missing_percent=(
                100.0 * missing[index] / row_count if row_count else 0.0
            ),
        )
        for index, name in enumerate(frame.columns)
    ]

    return DatasetProfile(
        row_count=row_count,
        column_count=frame.shape[1],
        duplicate_row_count=duplicate_count,
        columns=columns,
    )


def measure(operation: Callable[[], object]) -> dict[str, float]:
    """Warm up once, then report seven individual elapsed-time samples."""
    operation()
    samples = []

    for _ in range(REPEATS):
        gc.collect()
        started = perf_counter()
        operation()
        samples.append((perf_counter() - started) * 1_000)

    return {
        "median_ms": statistics.median(samples),
        "min_ms": min(samples),
        "max_ms": max(samples),
    }


def main() -> None:
    cases = []

    for row_count in ROW_COUNTS:
        content = make_csv(row_count)
        frame = load_csv_bytes(content)

        actual = profile_dataframe(frame)
        baseline = profile_with_row_loop(frame)
        if actual.model_dump() != baseline.model_dump():
            raise AssertionError(
                f"Baseline and profiler disagree for {row_count} rows."
            )

        pandas_timing = measure(lambda: profile_dataframe(frame))
        baseline_timing = measure(lambda: profile_with_row_loop(frame))
        load_timing = measure(lambda: load_csv_bytes(content))
        combined_timing = measure(
            lambda: profile_dataframe(load_csv_bytes(content))
        )

        cases.append(
            {
                "rows": row_count,
                "columns": frame.shape[1],
                "csv_bytes": len(content),
                "duplicate_rows": actual.duplicate_row_count,
                "missing_cells": sum(
                    column.missing_count for column in actual.columns
                ),
                "baseline_matches": True,
                "pandas_profile": pandas_timing,
                "row_loop_profile": baseline_timing,
                "csv_load": load_timing,
                "load_and_profile": combined_timing,
                "baseline_over_pandas_ratio": (
                    baseline_timing["median_ms"] / pandas_timing["median_ms"]
                ),
            }
        )

    report = {
        "measured_at_utc": datetime.now(timezone.utc).isoformat(),
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "packages": {
            package: version(package)
            for package in ("pandas", "numpy", "pydantic")
        },
        "repeats": REPEATS,
        "warmup_runs_per_operation": 1,
        "timing_unit": "milliseconds",
        "scope": (
            "Single-process, in-memory synthetic CSV benchmark. "
            "Excludes disk storage, HTTP, MCP, and browser rendering."
        ),
        "cases": cases,
    }

    output = Path(__file__).with_name("results.json")
    output.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print("Rows | Pandas ms | Row-loop ms | Load ms | Load+profile ms | Ratio")
    for case in cases:
        print(
            f"{case['rows']:>5} | "
            f"{case['pandas_profile']['median_ms']:>9.3f} | "
            f"{case['row_loop_profile']['median_ms']:>11.3f} | "
            f"{case['csv_load']['median_ms']:>7.3f} | "
            f"{case['load_and_profile']['median_ms']:>15.3f} | "
            f"{case['baseline_over_pandas_ratio']:>5.2f}x"
        )

    print("\nAll baseline comparisons matched.")
    print(f"Detailed results saved to: {output}")


if __name__ == "__main__":
    main()