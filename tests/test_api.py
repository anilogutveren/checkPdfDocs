"""Tests for the FastAPI backend."""

from __future__ import annotations

import io

import pymupdf
import pytest
from fastapi.testclient import TestClient

from contract_checker.api import app


@pytest.fixture(scope="module")
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture(scope="module")
def sample_pdf_bytes(tmp_path_factory) -> bytes:
    out = tmp_path_factory.mktemp("pdfs") / "sample.pdf"
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_textbox(
        (72, 72, 540, 720),
        "This contract is made between the parties for the provision of "
        "services. The terms of the agreement define the obligations of "
        "each party, the schedule of payments, and the term of the "
        "agreement. Both parties acknowledge that they have read the "
        "agreement and agree to its terms in full. This agreement "
        "constitutes the entire understanding between the parties and "
        "supersedes all prior discussions. Each party signs the signature "
        "block below to indicate acceptance of all terms and conditions "
        "set forth in this agreement, including the parties' respective "
        "duties and responsibilities under the contract.",
    )
    doc.save(str(out))
    return out.read_bytes()


def test_health(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_analyze_valid_pdf(client: TestClient, sample_pdf_bytes: bytes) -> None:
    response = client.post(
        "/analyze",
        files={"file": ("sample.pdf", io.BytesIO(sample_pdf_bytes), "application/pdf")},
        data={"use_llm": "false"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["filename"] == "sample.pdf"
    assert payload["use_llm"] is False
    assert payload["word_count"] >= 50
    assert all(result["passed"] for result in payload["results"])


def test_analyze_rejects_non_pdf(client: TestClient, sample_pdf_bytes: bytes) -> None:
    response = client.post(
        "/analyze",
        files={"file": ("sample.txt", io.BytesIO(b"not a pdf"), "text/plain")},
        data={"use_llm": "false"},
    )
    assert response.status_code == 422


def test_analyze_rejects_invalid_pdf(client: TestClient) -> None:
    response = client.post(
        "/analyze",
        files={
            "file": ("fake.pdf", io.BytesIO(b"not a real pdf"), "application/pdf")
        },
        data={"use_llm": "false"},
    )
    assert response.status_code == 422
