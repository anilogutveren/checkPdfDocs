"""Optional MLflow tracing of contract analyses.

Tracking is enabled only when ``MLFLOW_TRACKING_URI`` is set. Only metadata and
check results are logged, never the contract text itself.
"""

from __future__ import annotations

import logging
import os

from .models import CheckResult

logger = logging.getLogger(__name__)

TRACKING_URI_ENV = "MLFLOW_TRACKING_URI"
EXPERIMENT_ENV = "MLFLOW_EXPERIMENT_NAME"
DEFAULT_EXPERIMENT = "contract-checker"


def is_enabled() -> bool:
    """True when an MLflow tracking server has been configured."""
    return bool(os.environ.get(TRACKING_URI_ENV))


def record_analysis(source: str, word_count: int, results: list[CheckResult]) -> str | None:
    """Log the analysis as an MLflow trace with scorer feedback attached.

    Returns the trace id, or None when tracking is disabled or fails. Failures
    are logged and swallowed so tracking can never break an analysis.
    """
    if not is_enabled():
        return None
    try:
        return _log_analysis(source, word_count, results)
    except Exception:
        logger.warning("MLflow tracking failed; analysis result is unaffected.", exc_info=True)
        return None


def _log_analysis(source: str, word_count: int, results: list[CheckResult]) -> str:
    # Imported lazily: mlflow is slow to import and only needed when tracking is on.
    import mlflow
    from mlflow.entities import SpanType

    from .scoring import analysis_outputs, applicable_scorers

    mlflow.set_experiment(os.environ.get(EXPERIMENT_ENV, DEFAULT_EXPERIMENT))
    outputs = analysis_outputs(results)

    with mlflow.start_span(name="analyze_contract", span_type=SpanType.CHAIN) as span:
        span.set_inputs({"source": source, "word_count": word_count})
        span.set_outputs(outputs)
        trace_id = span.trace_id

    mlflow.flush_trace_async_logging()
    for check_scorer in applicable_scorers(outputs):
        mlflow.log_assessment(trace_id=trace_id, assessment=check_scorer(outputs=outputs))
    return trace_id
