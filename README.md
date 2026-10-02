# contract-checker

A tool for checking PDF contract files. It extracts the text of a contract PDF
and runs checks over it:

- **Heuristic checks** — look for the presence of expected contract sections
  (parties, terms, signature) and a minimum length.
- **LLM check (optional)** — asks the local **Nimble** model, served by
  Ollama and reached through the **TypeSafe SDK**, whether the text reads like
  a contract, returning a 0-1 plausibility score.

The layout is a standard `uv` project with a `src/` package:

```
contract-checker/
├── pyproject.toml
├── uv.lock
├── main.py                    # thin shim so `uv run main.py` keeps working
├── src/
│    └── contract_checker/
│        ├── __init__.py
│        ├── main.py           # CLI entry point
│        ├── pdf.py            # PDF text extraction (PyMuPDF)
│        ├── checks.py         # heuristic + LLM checks
│        └── models.py         # CheckResult data model
├── documents/
│    └── contract.pdf
└── tests/
```

## Requirements

- [uv](https://docs.astral.sh/uv/) — the Python package/project manager
- [Ollama](https://ollama.com/) 0.35 or later, with the `nimble` model pulled
- Python 3.14

## Setup

```bash
uv add typesafe-sdk pymupdf        # core deps (already added)
uv add --dev pytest               # test deps

# Ollama must be running, and the model pulled:
ollama pull nimble
```

Point the TypeSafe SDK at your local Ollama instance. The API key is a
placeholder — local Ollama ignores it:

```bash
export TYPESAFE_BASE_URL=http://localhost:11434
export TYPESAFE_API_KEY=ollama
export TYPESAFE_DEFAULT_MODEL=nimble
```

## Usage

Heuristic checks only (no network, fast):

```bash
uv run main.py documents/contract.pdf
```

Include the LLM check against local Nimble (slower on first run while the 9B
model loads):

```bash
uv run main.py --llm documents/contract.pdf
```

Example output:

```
[PASS] section: Required section(s) found.
[PASS] section: Required section(s) found.
[PASS] section: Required section(s) found.
[PASS] length: Contract length: 93 words (minimum 50).
[PASS] llm: Nimble contract-plausibility score 1.00 (threshold 0.50).
```

## Tests

```bash
uv run pytest
```

The tests exercise text extraction and the heuristic checks only, so they run
without a model. The `--llm` path hits Ollama and is not part of the test
suite.