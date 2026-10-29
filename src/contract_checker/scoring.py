"""MLflow scorers that grade the outcome of a contract analysis.

Every scorer receives ``outputs`` shaped like ``analysis_outputs()`` returns,
so the same scorers work for live tracing and ``mlflow.genai.evaluate``.
"""

from __future__ import annotations

from typing import Any

from mlflow.entities import AssessmentSource, AssessmentSourceType, Feedback
from mlflow.genai.scorers import Scorer, scorer

from .models import CheckResult

DECISION_THRESHOLD = 0.5
LLM_CHECK_NAME = "llm"

_SOURCE = AssessmentSource(
    source_type=AssessmentSourceType.CODE,
    source_id="contract_checker.scoring",
)

Outputs = dict[str, Any]


def analysis_outputs(results: list[CheckResult]) -> Outputs:
    """Convert check results into the ``outputs`` payload the scorers read."""
    return {
        "checks": [
            {
                "name": result.name,
                "passed": result.passed,
                "message": result.message,
                "score": result.score,
            }
            for result in results
        ]
    }


def _heuristic_checks(outputs: Outputs) -> list[dict[str, Any]]:
    return [c for c in outputs["checks"] if c["name"] != LLM_CHECK_NAME]


def _heuristic_ratio(outputs: Outputs) -> float:
    checks = _heuristic_checks(outputs)
    if not checks:
        return 0.0
    return sum(c["passed"] for c in checks) / len(checks)


def _llm_value(outputs: Outputs) -> float | None:
    return next(
        (
            c["score"]
            for c in outputs["checks"]
            if c["name"] == LLM_CHECK_NAME and c["score"] is not None
        ),
        None,
    )


def _combined_score(outputs: Outputs) -> float:
    llm = _llm_value(outputs)
    heuristic = _heuristic_ratio(outputs)
    return heuristic if llm is None else (heuristic + llm) / 2


def _feedback(name: str, value: float | bool, rationale: str) -> Feedback:
    return Feedback(name=name, value=value, rationale=rationale, source=_SOURCE)


@scorer
def heuristic_score(outputs: Outputs) -> Feedback:
    """Share of heuristic checks that passed (0-1)."""
    checks = _heuristic_checks(outputs)
    passed = sum(c["passed"] for c in checks)
    return _feedback(
        "heuristic_score",
        _heuristic_ratio(outputs),
        f"{passed} of {len(checks)} heuristic checks passed.",
    )


@scorer
def llm_score(outputs: Outputs) -> Feedback:
    """Nimble contract-plausibility score (0-1); errors when the LLM did not run."""
    value = _llm_value(outputs)
    if value is None:
        return Feedback(name="llm_score", error="LLM check was not run.", source=_SOURCE)
    return _feedback("llm_score", value, "Plausibility score returned by Nimble.")


@scorer
def contract_score(outputs: Outputs) -> Feedback:
    """Overall score: heuristic ratio, averaged with the LLM score when available."""
    llm = _llm_value(outputs)
    basis = "heuristic checks only" if llm is None else "mean of heuristic and LLM scores"
    return _feedback("contract_score", _combined_score(outputs), f"Based on {basis}.")


@scorer
def confidence(outputs: Outputs) -> Feedback:
    """How decisive the verdict is: distance of contract_score from the threshold, scaled to 0-1."""
    score = _combined_score(outputs)
    value = abs(score - DECISION_THRESHOLD) / DECISION_THRESHOLD
    return _feedback(
        "confidence",
        min(value, 1.0),
        f"contract_score {score:.2f} vs. threshold {DECISION_THRESHOLD:.2f}.",
    )


@scorer
def is_contract(outputs: Outputs) -> Feedback:
    """Pass/fail verdict: contract_score at or above the threshold."""
    score = _combined_score(outputs)
    verdict = score >= DECISION_THRESHOLD
    comparison = ">=" if verdict else "<"
    return _feedback(
        "is_contract",
        verdict,
        f"contract_score {score:.2f} {comparison} {DECISION_THRESHOLD:.2f}.",
    )


ALL_SCORERS: tuple[Scorer, ...] = (
    heuristic_score,
    llm_score,
    contract_score,
    confidence,
    is_contract,
)


def applicable_scorers(outputs: Outputs) -> list[Scorer]:
    """Scorers that produce a value for *outputs* (skips llm_score if the LLM did not run)."""
    if _llm_value(outputs) is None:
        return [s for s in ALL_SCORERS if s is not llm_score]
    return list(ALL_SCORERS)
