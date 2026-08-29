from functools import lru_cache
from pathlib import Path
from typing import Any

from google import genai
from google.genai import errors as genai_errors
from google.genai import types
from tenacity import (
    RetryCallState,
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
)

from ..config import get_settings
from ..logging import log
from .prompts import EXTRACTION_PROMPT
from .schema import BudgetRtiAnswers


@lru_cache
def _client() -> genai.Client:
    return genai.Client(api_key=get_settings().gemini_api_key)


def _is_busy(exc: BaseException) -> bool:
    """True only for temporary problems: Google overloaded, or we are rate limited."""
    if isinstance(exc, genai_errors.ServerError):
        return True
    if isinstance(exc, genai_errors.ClientError):
        return getattr(exc, "code", None) == 429
    return False


def _announce_retry(state: RetryCallState) -> None:
    exc = state.outcome.exception() if state.outcome else None
    log.warning("gemini_busy_retrying", attempt=state.attempt_number, error=type(exc).__name__)


@retry(
    retry=retry_if_exception(_is_busy),
    wait=wait_exponential(multiplier=2, min=4, max=30),
    stop=stop_after_attempt(5),
    before_sleep=_announce_retry,
    reraise=True,
)
def _generate(contents: list[Any], source: str) -> BudgetRtiAnswers:
    """One call to Gemini, whatever the input was. Retries while Google is busy."""
    settings = get_settings()

    response = _client().models.generate_content(
        model=settings.gemini_model,
        contents=contents,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=BudgetRtiAnswers,
            temperature=0,
            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
        ),
    )

    usage = response.usage_metadata
    log.info(
        "gemini_call",
        source=source,
        model=settings.gemini_model,
        input_tokens=getattr(usage, "prompt_token_count", None),
        output_tokens=getattr(usage, "candidates_token_count", None),
    )

    if response.text is None:
        raise RuntimeError("Gemini returned no text")
    return BudgetRtiAnswers.model_validate_json(response.text)


def extract_from_text(text: str) -> BudgetRtiAnswers:
    """For documents whose words are already in the file."""
    return _generate([EXTRACTION_PROMPT, "--- DOCUMENT TEXT ---", text], source="text")


def extract_from_images(image_paths: list[Path]) -> BudgetRtiAnswers:
    """For scans - one picture per page, in page order."""
    pages: list[Any] = [
        types.Part.from_bytes(data=path.read_bytes(), mime_type="image/png") for path in image_paths
    ]
    contents: list[Any] = [EXTRACTION_PROMPT, "--- DOCUMENT PAGES, IN ORDER ---", *pages]
    return _generate(contents, source=f"images:{len(pages)}")
