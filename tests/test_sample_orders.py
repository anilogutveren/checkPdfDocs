"""Ground-truth tests against the synthetic sample orders."""

from __future__ import annotations

import io
from pathlib import Path
from types import ModuleType

import pymupdf
import pytest
from fastapi.testclient import TestClient

from contract_checker.api import app
from contract_checker.checks import run_checks
from contract_checker.pdf import extract_text
from contract_checker.scoring import analysis_outputs, confidence, contract_score, heuristic_score, is_contract

from conftest import load_ground_truth

GROUND_TRUTH = load_ground_truth()
ORDER_IDS = [order["file_name"].removesuffix(".pdf") for order in GROUND_TRUTH]
MIN_WORDS = 1000


def _pdf(sample_orders_dir: Path, truth: dict) -> Path:
    return sample_orders_dir / truth["file_name"]


def _normalised_text(path: Path) -> str:
    return " ".join(extract_text(str(path)).split())


def test_ground_truth_covers_every_generated_order(order_generator: ModuleType) -> None:
    generated = {order.file_name for order in order_generator.SAMPLE_ORDERS}
    assert generated == {truth["file_name"] for truth in GROUND_TRUTH}


@pytest.mark.parametrize("truth", GROUND_TRUTH, ids=ORDER_IDS)
def test_page_count(sample_orders_dir: Path, truth: dict) -> None:
    with pymupdf.open(_pdf(sample_orders_dir, truth)) as doc:
        assert doc.page_count == truth["page_count"]


@pytest.mark.parametrize("truth", GROUND_TRUTH, ids=ORDER_IDS)
def test_extracted_text_contains_fields(sample_orders_dir: Path, truth: dict) -> None:
    text = _normalised_text(_pdf(sample_orders_dir, truth))
    missing = [name for name, value in truth["fields"].items() if value not in text]
    assert not missing, f"fields not found in extracted text: {missing}"


@pytest.mark.parametrize("truth", GROUND_TRUTH, ids=ORDER_IDS)
def test_extracted_text_contains_totals(sample_orders_dir: Path, truth: dict) -> None:
    text = _normalised_text(_pdf(sample_orders_dir, truth))
    missing = [name for name, value in truth["totals"].items() if name != "discount_percent" and value not in text]
    assert not missing, f"totals not found in extracted text: {missing}"


@pytest.mark.parametrize("truth", GROUND_TRUTH, ids=ORDER_IDS)
def test_generator_totals_match_ground_truth(order_generator: ModuleType, truth: dict) -> None:
    order = next(o for o in order_generator.SAMPLE_ORDERS if o.file_name == truth["file_name"])
    totals = order_generator.compute_totals(order)
    fmt = order_generator.format_eur
    expected = truth["totals"]
    assert fmt(totals.list_sum) == expected["list_sum"]
    assert fmt(totals.purchase_gross) == expected["purchase_gross"]
    assert fmt(totals.payment_after_handover + totals.transfer_gross) == expected["purchase_gross"]


@pytest.mark.parametrize("truth", GROUND_TRUTH, ids=ORDER_IDS)
def test_run_checks_match_expected(sample_orders_dir: Path, truth: dict) -> None:
    results = run_checks(extract_text(str(_pdf(sample_orders_dir, truth))))
    assert [r.passed for r in results] == truth["expected_checks"]


@pytest.mark.parametrize("truth", GROUND_TRUTH, ids=ORDER_IDS)
def test_length_check_reports_full_document(sample_orders_dir: Path, truth: dict) -> None:
    text = extract_text(str(_pdf(sample_orders_dir, truth)))
    assert len(text.split()) >= MIN_WORDS


@pytest.mark.parametrize("truth", GROUND_TRUTH, ids=ORDER_IDS)
def test_scores_match_expected(sample_orders_dir: Path, truth: dict) -> None:
    outputs = analysis_outputs(run_checks(extract_text(str(_pdf(sample_orders_dir, truth)))))
    expected = truth["expected_scores"]
    actual = {
        "heuristic_score": heuristic_score(outputs=outputs).value,
        "contract_score": contract_score(outputs=outputs).value,
        "confidence": confidence(outputs=outputs).value,
    }
    assert actual == pytest.approx({k: expected[k] for k in actual})
    assert is_contract(outputs=outputs).value is expected["is_contract"] is truth["is_contract"]


@pytest.mark.parametrize("truth", GROUND_TRUTH, ids=ORDER_IDS)
def test_analyze_endpoint_matches_expected(sample_orders_dir: Path, truth: dict) -> None:
    pdf_bytes = _pdf(sample_orders_dir, truth).read_bytes()
    response = TestClient(app).post(
        "/analyze",
        files={"file": (truth["file_name"], io.BytesIO(pdf_bytes), "application/pdf")},
        data={"use_llm": "false"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["filename"] == truth["file_name"]
    assert [r["passed"] for r in payload["results"]] == truth["expected_checks"]
