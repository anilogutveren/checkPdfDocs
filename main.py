"""Thin shim so `uv run main.py <contract.pdf>` keeps working after the src/ move.

The implementation now lives in `src/contract_checker/`.
"""

from contract_checker.main import main


if __name__ == "__main__":
    raise SystemExit(main())
