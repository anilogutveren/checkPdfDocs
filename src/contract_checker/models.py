"""Data models for contract checks."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CheckResult:
    """Outcome of a single contract check."""

    name: str
    passed: bool
    message: str
    score: float | None = None

    def __str__(self) -> str:
        status = "PASS" if self.passed else "FAIL"
        return f"[{status}] {self.name}: {self.message}"
