"""PDF text extraction using pymupdf (PyMuPDF)."""

from __future__ import annotations

import pymupdf  # PyMuPDF


def extract_text(pdf_path: str) -> str:
    """Extract the full text content of a PDF file.

    Args:
        pdf_path: Path to a PDF file.

    Returns:
        The concatenated text of all pages, separated by page breaks.
    """
    with pymupdf.open(pdf_path) as document:
        pages = [page.get_text() for page in document]
    return "\n".join(pages)
