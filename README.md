# DataBridge MCP — AI Dataset Inspector

Inspect CSV datasets through a browser, HTTP endpoints, or MCP tools.

DataBridge validates uploaded CSV files, stores them locally, and provides dataset profiles, bounded previews, and numeric or categorical column summaries. FastAPI and MCP share the same analysis functions and SQLite database.

This is a local portfolio project. It does not require an LLM, API key, or paid service.

## Features

- CSV uploads with encoding, size, shape, and header validation
- Persistent local storage with generated dataset IDs
- Row counts, inferred column types, missing-value statistics, and duplicate counts
- Bounded row previews with explicit missing-value and truncation indicators
- Numeric summaries: minimum, maximum, mean, and median
- Categorical summaries: frequencies, percentages, and omitted-category counts
- Browser interface for uploading and inspecting datasets
- Real MCP tools verified with MCP Inspector and subprocess integration tests

## Architecture

| Component | Responsibility |
|---|---|
| `databridge/` | CSV validation, storage, profiling, previews, and summaries |
| `api.py` | FastAPI upload and inspection endpoints |
| `mcp_server.py` | MCP tools served over stdio |
| `web.py` | API application with the browser home page |
| `static/index.html` | HTML/CSS/JavaScript inspection interface |
| `tests/` | Analysis, storage, HTTP, and MCP integration tests |
| `benchmarks/` | Reproducible profiling comparison |

MCP clients discover tools and call predefined operations. The browser uses HTTP endpoints. Both adapters call the shared Python analysis layer.

No tool accepts arbitrary Python code or unrestricted filesystem paths.

## Requirements

Verified locally with:

- Windows
- Python 3.11.3
- Node.js 24.15.0 and npm 12.0.1 for MCP Inspector

Python dependencies are pinned in `requirements.txt`.

The dependency snapshot was generated and tested on Windows and includes Windows-specific packages. Linux and macOS installation have not been verified.

## Run locally

Open Command Prompt in the project root:

```bat
py -3.11 -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
python -m pip check
```

Start the browser application:

```bat
python -m uvicorn web:create_web_app --factory --host 127.0.0.1 --port 8000
```

Open:

- Interface: http://127.0.0.1:8000/
- API documentation: http://127.0.0.1:8000/docs

Use `examples/upload_demo.csv` for a small demonstration.

The sample should produce:

- 3 rows and 2 columns
- 1 duplicate row
- 1 missing age, approximately 33.33%
- Mean and median age of 24
- Name frequencies: Nila = 2, Rafi = 1

Press Ctrl+C to stop the server.

### API-only application

```bat
python -m uvicorn api:create_app --factory --host 127.0.0.1 --port 8000
```

The API-only application provides `/docs` and the dataset endpoints, but no home page at `/`.

## HTTP endpoints

| Method | Route | Purpose |
|---|---|---|
| POST | `/datasets` | Upload and validate a CSV |
| GET | `/datasets?limit=20` | List stored datasets, newest first |
| GET | `/datasets/{dataset_id}/profile` | Profile a dataset |
| GET | `/datasets/{dataset_id}/preview?limit=5` | Preview its first rows |
| GET | `/datasets/{dataset_id}/summary?column=age&mode=numeric` | Summarize a column |

Categorical summaries use `mode=categorical` and optionally `top_k`, with a default of 5 and maximum of 20.

Column names are query parameters, so names containing spaces can be supplied without changing the route.

Expected HTTP responses include:

- `201`: dataset created
- `400`: invalid CSV, filename, or column-analysis request
- `404`: dataset not found
- `413`: uploaded file exceeds the endpoint's size limit
- `422`: missing or invalid request parameters

## MCP tools

| Tool | Purpose |
|---|---|
| `get_server_info` | Report server identity and development status |
| `list_datasets` | Discover stored dataset IDs |
| `profile_dataset` | Profile one dataset |
| `preview_dataset` | Return a bounded display preview |
| `summarize_column` | Run numeric or categorical column analysis |

Upload a dataset through the browser or HTTP API first.

In another Command Prompt terminal, activate the environment and list tools:

```bat
.venv\Scripts\activate
npx -y @modelcontextprotocol/inspector --cli ".venv\Scripts\python.exe" mcp_server.py --method tools/list
```

List stored datasets:

```bat
npx -y @modelcontextprotocol/inspector --cli ".venv\Scripts\python.exe" mcp_server.py --method tools/call --tool-name list_datasets
```

Set the dataset ID using the actual value returned by upload or listing:

```bat
set "DATASET_ID=REPLACE_WITH_ACTUAL_DATASET_ID"
```

Profile the dataset:

```bat
npx -y @modelcontextprotocol/inspector --cli ".venv\Scripts\python.exe" mcp_server.py --method tools/call --tool-name profile_dataset --tool-arg dataset_id=%DATASET_ID%
```

Preview it:

```bat
npx -y @modelcontextprotocol/inspector --cli ".venv\Scripts\python.exe" mcp_server.py --method tools/call --tool-name preview_dataset --tool-arg dataset_id=%DATASET_ID% --tool-arg limit=5
```

Summarize the sample's age column:

```bat
npx -y @modelcontextprotocol/inspector --cli ".venv\Scripts\python.exe" mcp_server.py --method tools/call --tool-name summarize_column --tool-arg dataset_id=%DATASET_ID% --tool-arg column=age --tool-arg mode=numeric
```

Inspector launches the MCP server as a subprocess. A separate manually started MCP server is unnecessary.

FastAPI does not need to remain running when MCP inspects previously stored data.

Inspector is fetched through npm; its version is not pinned by the Python requirements file.

## Data policies

### CSV validation

- UTF-8 encoding, with an optional byte-order mark
- Comma delimiter and a required header record
- Maximum file size: 5 MiB
- Maximum data rows: 10,000
- Maximum columns: 100
- Unique, nonblank column names
- Every data record must match the header width
- Header-only datasets are accepted
- Null bytes are rejected
- Empty fields are missing; literal `NA` and `NULL` are preserved

Column types are inferred by pandas. Numeric-looking identifiers can therefore lose formatting such as leading zeros in parsed views. Original uploaded bytes remain stored.

### Profiles and previews

Duplicate counts exclude the first occurrence of each repeated row.

Previews return at most 50 rows. Nonmissing cells are display strings; missing cells become JSON `null`. Cells longer than 200 characters are shortened and counted.

A preview represents parsed data, not a lossless CSV export.

### Column summaries

Numeric statistics use finite values only. Missing values and infinities are counted separately. If no finite values remain, statistics are `null`.

Numeric summaries use floating-point values and are not intended for exact accounting or precision-sensitive large-integer calculations.

Categorical percentages use nonmissing rows as the denominator. Values are counted before display labels are shortened. Omitted categories and their combined row count are reported.

Long category labels may look identical after shortening; truncation flags identify this limitation.

## Tests

Run:

```bat
python -m pytest -q
```

Verified result: **91 passing tests**.

Coverage includes:

- Profiling calculations and input preservation
- CSV validation and resource-limit boundaries
- Persistent storage and dataset isolation
- HTTP uploads, inspection, summaries, and error responses
- MCP tool discovery, calls, and errors through real stdio subprocesses

A separate fresh Python 3.11 environment installed `requirements.txt`, passed `pip check`, and ran all 91 tests successfully on Windows.

Browser workflows were checked manually. There is no automated browser test suite.

## Performance evaluation

Run:

```bat
python -m benchmarks.run_benchmarks
```

The benchmark generates deterministic four-column CSV datasets, verifies equivalent results against a row-loop baseline, and saves environment details and measurements in `benchmarks/results.json`.

Each operation receives one warm-up run followed by seven timed runs. The table reports median elapsed time.

| Rows | Pandas profile | Row-loop profile | CSV loading | Load + profile | Baseline / pandas |
|---:|---:|---:|---:|---:|---:|
| 100 | 1.194 ms | 0.847 ms | 1.633 ms | 2.171 ms | 0.71× |
| 1,000 | 1.438 ms | 4.751 ms | 1.752 ms | 3.443 ms | 3.30× |
| 10,000 | 4.040 ms | 40.696 ms | 12.993 ms | 15.087 ms | 10.07× |

Both implementations returned identical profiles for all three datasets.

The row-loop baseline was faster at 100 rows. The pandas profiler was approximately 10.07× faster at 10,000 rows.

These are local, single-process measurements on synthetic data. They exclude database access, HTTP, MCP transport, and browser rendering. Separately measured operation medians are not expected to sum exactly.

## Storage and limitations

- Data is stored in `data/datasets.sqlite3`, excluded from Git.
- Repeated uploads create separate datasets, even with identical filenames.
- There is no authentication or per-user isolation; run this demo on localhost.
- Storage has no aggregate quota or dataset-deletion endpoint.
- Listing returns at most the newest 100 datasets; pagination is not implemented.
- Upload size checks bound the endpoint's file read, not the entire incoming HTTP request. Multipart parsing may spool content before the endpoint runs.
- CSV data is reparsed on inspection; there is no analysis cache.
- MCP transport is local stdio; remote MCP hosting is not implemented.
- No LLM integration is included. MCP clients can call the inspection tools without a model.
- The project is a local prototype, not a production-ready service.