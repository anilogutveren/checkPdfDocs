# Smart PDF Analyser

A tool for checking PDF contract files. It extracts the text of a contract PDF
and runs checks over it:

- **Heuristic checks** — look for the presence of expected contract sections
  (parties, terms, signature) and a minimum length.
- **LLM check (optional)** — asks the local **Nimble** model, served by
  Ollama and reached through the **TypeSafe SDK**, whether the text reads like
  a contract, returning a 0-1 plausibility score.

The project now includes both a command-line interface and a modern web UI
built with **React + TypeScript**, **shadcn/ui**, **Tailwind CSS** and a
**FastAPI** backend.

```
checkPdfProject/
├── main.py                          # CLI shim
├── ui.py                            # one-command UI launcher
├── docker-compose.yml               # local MLflow tracking server
├── pyproject.toml
├── uv.lock
├── src/
│   └── contract_checker/
│       ├── __init__.py
│       ├── main.py                  # CLI entry point
│       ├── api.py                   # FastAPI backend
│       ├── checks.py                # heuristic + LLM checks
│       ├── pdf.py                   # PDF text extraction (PyMuPDF)
│       └── models.py                # CheckResult data model
├── frontend/                        # React UI
├── documents/
│   └── contract.pdf
└── tests/
```

## Requirements

- [uv](https://docs.astral.sh/uv/) — the Python package/project manager
- [Node.js](https://nodejs.org/) 20+ and npm — for the React frontend
- [Ollama](https://ollama.com/) 0.35 or later, with the `nimble` model pulled
- Python 3.14

## Setup

```bash
uv sync

# Frontend dependencies (only needed once or when packages change)
cd frontend
npm install
```

Point the TypeSafe SDK at your local Ollama instance. The API key is a
placeholder — local Ollama ignores it:

```bash
export TYPESAFE_BASE_URL=http://localhost:11434
export TYPESAFE_API_KEY=ollama
export TYPESAFE_DEFAULT_MODEL=nimble
```

## Command-line usage

Heuristic checks only (no network, fast):

```bash
uv run main.py documents/contract.pdf
```

Include the LLM check against local Nimble:

```bash
uv run main.py --llm documents/contract.pdf
```

## Web UI usage

Launch the development UI (FastAPI backend + Vite frontend + browser):

```bash
uv run ui.py
```

Build the production frontend and serve it through FastAPI on a single port:

```bash
uv run ui.py --serve
```

In the UI, drag a PDF onto the drop zone (or click to browse), optionally
enable **Use LLM**, then click **Scan & Analyse**. Results are shown on the
right side.

## MLflow (Docker)

A local MLflow 3.17.2 tracking server is defined in `docker-compose.yml`.
Runs are stored in the `mlflow-data` Docker volume.

```bash
docker compose up -d
docker compose ps                                # wait for "healthy"
export MLFLOW_TRACKING_URI=http://localhost:5001
```

The UI is at <http://localhost:5001>. The server binds to `127.0.0.1` only;
set `MLFLOW_PORT` to change the host port (5000 is taken by macOS AirPlay).

Stop it with `docker compose down` (add `-v` to also delete stored runs).

### Tracing and scores

When `MLFLOW_TRACKING_URI` is set, every analysis (CLI and `/analyze`) is
logged as a trace in the `contract-checker` experiment (override with
`MLFLOW_EXPERIMENT_NAME`). Only the file name, word count and check results
are logged — never the contract text. Tracking failures are logged as
warnings and never break an analysis.

Each trace gets feedback from the `@scorer` functions in
`src/contract_checker/scoring.py`:

| Scorer            | Value | Meaning                                                        |
|-------------------|-------|----------------------------------------------------------------|
| `heuristic_score` | 0-1   | Share of heuristic checks that passed                          |
| `llm_score`       | 0-1   | Nimble plausibility score (only when `--llm` / Use LLM is on)  |
| `contract_score`  | 0-1   | Heuristic share, averaged with `llm_score` when available      |
| `confidence`      | 0-1   | Distance of `contract_score` from the 0.5 threshold, scaled    |
| `is_contract`     | bool  | `contract_score >= 0.5`                                        |

The same scorers can be passed to `mlflow.genai.evaluate(scorers=...)`.

See [docs/mlflow-experiment-tracking.md](docs/mlflow-experiment-tracking.md)
for the full guide.

## Tests

```bash
uv run pytest
```

The tests exercise text extraction, the heuristic checks, and the FastAPI
`/analyze` endpoint. The `--llm` path hits Ollama and is not part of the
test suite.
