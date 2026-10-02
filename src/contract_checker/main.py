"""Command-line entry point for contract_checker."""

from .pdf import extract_text
from .checks import run_checks
from .models import CheckResult

import sys


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    use_llm = "--llm" in sys.argv[1:]

    if not args:
        print("usage: uv run main.py [--llm] <path-to-contract.pdf>", file=sys.stderr)
        return 2

    pdf_path = args[0]
    try:
        text = extract_text(pdf_path)
    except FileNotFoundError:
        print(f"error: file not found: {pdf_path}", file=sys.stderr)
        return 1

    results: list[CheckResult] = run_checks(text)
    if use_llm:
        from .checks import llm_contract_check

        results.append(llm_contract_check(text))

    for result in results:
        print(result)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
