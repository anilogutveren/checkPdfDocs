"""Contract checks: heuristic and LLM-assisted validation of contract text."""

from __future__ import annotations

from .models import CheckResult


_MAX_LLM_BYTES = 60_000


def _truncate_to_bytes(text: str, max_bytes: int = _MAX_LLM_BYTES) -> str:
    """Return the start of *text* truncated to at most *max_bytes* UTF-8 bytes."""
    encoded = text.encode("utf-8")
    if len(encoded) <= max_bytes:
        return text
    return encoded[:max_bytes].decode("utf-8", errors="ignore")


def _require(section_keywords: list[str], text: str) -> CheckResult:
    """Pass if at least one keyword appears in the text (case-insensitive)."""
    lowered = text.lower()
    found = any(keyword.lower() in lowered for keyword in section_keywords)
    return CheckResult(
        name="section",
        passed=found,
        message=(
            "Required section(s) found."
            if found
            else f"Missing expected section(s): {', '.join(section_keywords)}"
        ),
    )


def run_checks(text: str) -> list[CheckResult]:
    """Run the contract checks over extracted PDF text.

    Args:
        text: Raw text extracted from the contract PDF.

    Returns:
        A list of CheckResult objects, one per check.
    """
    results: list[CheckResult] = []

    results.append(_require(["parties", "party"], text))
    results.append(_require(["terms", "term"], text))
    results.append(_require(["signature", "sign", "agreement"], text))

    word_count = len(text.split())
    results.append(
        CheckResult(
            name="length",
            passed=word_count >= 50,
            message=f"Contract length: {word_count} words (minimum 50).",
        )
    )

    return results


def llm_contract_check(text: str, threshold: float = 0.5) -> CheckResult:
    """Ask the local Nimble model (via TypeSafe) whether the text is a contract.

    The match score returned by the model is treated as a 0-1 plausibility
    score. Any failure to reach the model is reported as a non-passing result
    rather than raised, so callers can keep going with the heuristic checks.

    Args:
        text: Contract text to evaluate.
        threshold: Minimum match score to pass (default 0.5).

    Returns:
        A CheckResult for the "llm" check.
    """
    from typesafe_sdk import Noul, TypeSafeClient

    prompt = (
        "Read the text below. If it reads like a legal contract or agreement, "
        "match it. Output a single word."
    )
    safe_text = _truncate_to_bytes(text)
    try:
        with TypeSafeClient(timeout=180.0) as client:
            result = client.system_one(
                state=safe_text,
                questions={"is_contract": Noul(instructions=prompt)},
            )
        score = float(result.answers["is_contract"].noul)
    except Exception as exc:    # pragma: no cover - network/model errors
        return CheckResult(
            name="llm",
            passed=False,
            message=f"LLM check unavailable ({type(exc).__name__}: {exc})",
        )

    return CheckResult(
        name="llm",
        passed=score >= threshold,
        message=(
            f"Nimble contract-plausibility score {score:.2f} "
            f"(threshold {threshold:.2f})."
        ),
        score=score,
    )