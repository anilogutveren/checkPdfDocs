"""Tests for contract_checker."""

from __future__ import annotations

import pymupdf
import pytest

from contract_checker.pdf import extract_text
from contract_checker.checks import run_checks


@pytest.fixture(scope="module")
def sample_pdf(tmp_path_factory) -> str:
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
    return str(out)


def test_extract_text(sample_pdf: str) -> None:
    text = extract_text(sample_pdf)
    assert "parties" in text
    assert "terms" in text


def test_run_checks_pass_on_valid_contract(sample_pdf: str) -> None:
    text = extract_text(sample_pdf)
    results = run_checks(text)
    assert results, "expected at least one check to run"
    assert all(result.passed for result in results)


def test_run_checks_fail_on_short_contract() -> None:
    results = run_checks("too short")
    length = next(r for r in results if r.name == "length")
    assert not length.passed
