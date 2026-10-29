"""Tests for the MLflow scorers and the optional tracking hook."""

from __future__ import annotations

import pytest

from contract_checker import tracking
from contract_checker.models import CheckResult
from contract_checker.scoring import (
    analysis_outputs,
    applicable_scorers,
    confidence,
    contract_score,
    heuristic_score,
    is_contract,
    llm_score,
)

ALL_PASS = [CheckResult("section", True, "ok"), CheckResult("length", True, "ok")]
HALF_PASS = [CheckResult("section", True, "ok"), CheckResult("length", False, "short")]


def _outputs(results: list[CheckResult], llm: float | None = None) -> dict:
    if llm is not None:
        results = [*results, CheckResult("llm", llm >= 0.5, "llm", score=llm)]
    return analysis_outputs(results)


def test_heuristic_score_is_share_of_passed_checks() -> None:
    assert heuristic_score(outputs=_outputs(HALF_PASS)).value == 0.5


def test_heuristic_score_ignores_llm_check() -> None:
    assert heuristic_score(outputs=_outputs(ALL_PASS, llm=0.0)).value == 1.0


def test_contract_score_averages_heuristic_and_llm() -> None:
    assert contract_score(outputs=_outputs(ALL_PASS, llm=0.6)).value == pytest.approx(0.8)


def test_contract_score_without_llm_uses_heuristic_only() -> None:
    assert contract_score(outputs=_outputs(HALF_PASS)).value == 0.5


@pytest.mark.parametrize(
    ("results", "llm", "expected"),
    [(ALL_PASS, None, 1.0), (HALF_PASS, None, 0.0), (ALL_PASS, 0.0, 0.0)],
)
def test_confidence_is_distance_from_threshold(results, llm, expected) -> None:
    assert confidence(outputs=_outputs(results, llm)).value == pytest.approx(expected)


def test_is_contract_true_at_threshold() -> None:
    assert is_contract(outputs=_outputs(HALF_PASS)).value is True


def test_is_contract_false_below_threshold() -> None:
    results = [CheckResult("section", False, "missing"), CheckResult("length", True, "ok")]
    assert is_contract(outputs=_outputs(results, llm=0.1)).value is False


def test_llm_score_reports_error_when_llm_not_run() -> None:
    feedback = llm_score(outputs=_outputs(ALL_PASS))
    assert feedback.value is None
    assert feedback.error is not None


def test_applicable_scorers_skip_llm_when_not_run() -> None:
    assert llm_score not in applicable_scorers(_outputs(ALL_PASS))


def test_applicable_scorers_include_llm_when_run() -> None:
    assert llm_score in applicable_scorers(_outputs(ALL_PASS, llm=0.9))


def test_record_analysis_disabled_without_tracking_uri(monkeypatch) -> None:
    monkeypatch.delenv(tracking.TRACKING_URI_ENV, raising=False)
    assert tracking.record_analysis("a.pdf", 10, ALL_PASS) is None


def test_record_analysis_swallows_tracking_errors(monkeypatch) -> None:
    def boom(*_args):
        raise ConnectionError("server down")

    monkeypatch.setenv(tracking.TRACKING_URI_ENV, "http://localhost:1")
    monkeypatch.setattr(tracking, "_log_analysis", boom)
    assert tracking.record_analysis("a.pdf", 10, ALL_PASS) is None


def test_record_analysis_logs_trace_with_scores(monkeypatch, tmp_path) -> None:
    import mlflow

    monkeypatch.setenv(tracking.TRACKING_URI_ENV, f"sqlite:///{tmp_path / 'mlflow.db'}")
    mlflow.set_tracking_uri(f"sqlite:///{tmp_path / 'mlflow.db'}")

    trace_id = tracking.record_analysis("a.pdf", 10, [*ALL_PASS, CheckResult("llm", True, "x", 0.9)])

    names = {a.name for a in mlflow.get_trace(trace_id).info.assessments}
    assert names == {"heuristic_score", "llm_score", "contract_score", "confidence", "is_contract"}
