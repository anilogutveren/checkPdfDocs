"""Shared fixtures: synthetic sample orders and their ground truth."""

from __future__ import annotations

import importlib.util
import json
import os
import sys
from pathlib import Path
from types import ModuleType

import mlflow
import pytest

from contract_checker.tracking import EXPERIMENT_ENV, TRACKING_URI_ENV

ROOT = Path(__file__).resolve().parent.parent
GENERATOR_PATH = ROOT / "scripts" / "generate_sample_orders.py"
GROUND_TRUTH_PATH = Path(__file__).resolve().parent / "fixtures" / "sample_orders_ground_truth.json"
TEST_EXPERIMENT_ENV = "MLFLOW_TEST_EXPERIMENT_NAME"
DEFAULT_TEST_EXPERIMENT = "contract-checker-tests"


def load_ground_truth() -> list[dict]:
    """Expected values per sample order (used for parametrisation at collection time)."""
    return json.loads(GROUND_TRUTH_PATH.read_text(encoding="utf-8"))["orders"]


@pytest.fixture(scope="session")
def mlflow_tracking_uri(tmp_path_factory: pytest.TempPathFactory) -> str:
    """The configured MLflow server if MLFLOW_TRACKING_URI is set, else an isolated SQLite store."""
    configured_uri = os.environ.get(TRACKING_URI_ENV)
    if configured_uri:
        return configured_uri
    return f"sqlite:///{tmp_path_factory.mktemp('mlflow') / 'mlflow.db'}"


@pytest.fixture(scope="session")
def mlflow_test_experiment() -> str:
    """Separate experiment so test traces never mix with real analyses."""
    return os.environ.get(TEST_EXPERIMENT_ENV, DEFAULT_TEST_EXPERIMENT)


@pytest.fixture(autouse=True)
def _mlflow_tracking(
    mlflow_tracking_uri: str, mlflow_test_experiment: str, monkeypatch: pytest.MonkeyPatch
) -> str:
    monkeypatch.setenv(TRACKING_URI_ENV, mlflow_tracking_uri)
    monkeypatch.setenv(EXPERIMENT_ENV, mlflow_test_experiment)
    # Reset explicitly: an earlier mlflow.set_tracking_uri() call would otherwise override the env var.
    mlflow.set_tracking_uri(mlflow_tracking_uri)
    return mlflow_tracking_uri


@pytest.fixture(scope="session")
def order_generator() -> ModuleType:
    spec = importlib.util.spec_from_file_location("generate_sample_orders", GENERATOR_PATH)
    module = importlib.util.module_from_spec(spec)
    # dataclasses resolve their module through sys.modules, so register before executing.
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="session")
def sample_orders_dir(order_generator: ModuleType, tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Sample PDFs are gitignored, so build them fresh for every test session."""
    output_dir = tmp_path_factory.mktemp("sample_orders")
    order_generator.generate(output_dir)
    return output_dir
