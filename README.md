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

## Tests

```bash
uv run pytest
```

The tests exercise text extraction, the heuristic checks, and the FastAPI
`/analyze` endpoint. The `--llm` path hits Ollama and is not part of the
test suite.
