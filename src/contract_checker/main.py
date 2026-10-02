"""Command-line entry point for contract_checker."""

from .pdf import extract_text
from .checks import run_checks
from .models import CheckResult

import sys


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: uv run main.py <path-to-contract.pdf>", file=sys.stderr)
        return 2

    pdf_path = sys.argv[1]
    try:
        text = extract_text(pdf_path)
    except FileNotFoundError:
        print(f"error: file not found: {pdf_path}", file=sys.stderr)
        return 1

    results: list[CheckResult] = run_checks(text)
    for result in results:
        print(result)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
