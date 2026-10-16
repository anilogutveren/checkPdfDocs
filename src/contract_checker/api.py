"""FastAPI backend for the Smart PDF Analyser UI."""

from __future__ import annotations

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, File, Form, UploadFile, status
from fastapi.exceptions import HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .checks import llm_contract_check, run_checks
from .pdf import extract_text_from_bytes


class CheckResultItem(BaseModel):
    """One contract check result returned to the frontend."""

    name: str
    passed: bool
    message: str


class AnalyzeResponse(BaseModel):
    """Response body for POST /analyze."""

    filename: str
    word_count: int
    use_llm: bool
    results: list[CheckResultItem]


class HealthResponse(BaseModel):
    """Response body for GET /health."""

    status: str


def _make_app() -> FastAPI:
    app = FastAPI(title="Smart PDF Analyser API")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health", response_model=HealthResponse)
    async def health() -> HealthResponse:
        return HealthResponse(status="ok")

    @app.post("/analyze", response_model=AnalyzeResponse)
    async def analyze(
        file: UploadFile = File(...),
        use_llm: bool = Form(False),
    ) -> AnalyzeResponse:
        if file.content_type != "application/pdf":
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Only PDF files are supported.",
            )

        try:
            pdf_bytes = await file.read()
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to read uploaded file.",
            ) from exc

        if not pdf_bytes:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Uploaded file is empty.",
            )

        if not pdf_bytes.startswith(b"%PDF"):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="The uploaded file is not a valid PDF.",
            )

        try:
            text = extract_text_from_bytes(pdf_bytes)
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Could not extract text from the PDF.",
            ) from exc

        results = run_checks(text)
        if use_llm:
            results.append(llm_contract_check(text))

        return AnalyzeResponse(
            filename=file.filename or "contract.pdf",
            word_count=len(text.split()),
            use_llm=use_llm,
            results=[
                CheckResultItem(
                    name=result.name,
                    passed=result.passed,
                    message=result.message,
                )
                for result in results
            ],
        )

    return app


app = _make_app()

# Serve a built React app when FRONTEND_STATIC_DIR is set (production / --serve mode).
_static_dir = os.environ.get("FRONTEND_STATIC_DIR")
if _static_dir and os.path.isdir(_static_dir):
    app.mount("/", StaticFiles(directory=_static_dir, html=True), name="static")
