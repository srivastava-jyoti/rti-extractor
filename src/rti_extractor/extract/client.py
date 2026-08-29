from functools import lru_cache
from pathlib import Path
from typing import Any

from google import genai
from google.genai import errors as genai_errors
from google.genai import types
from pydantic import BaseModel
from tenacity import (
    RetryCallState,
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
)

from ..config import get_settings
from ..logging import log
from ..rti_type import RtiTypeDef
from .prompts import build_prompt
from .schema import build_answers_model


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
def _generate(rti_type: RtiTypeDef, contents: list[Any], source: str) -> BaseModel:
    """One call to Gemini, whatever the input was. Retries while Google is busy."""
    settings = get_settings()
    answers_model = build_answers_model(rti_type)

    response = _client().models.generate_content(
        model=settings.gemini_model,
        contents=contents,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=answers_model,
            temperature=0,
            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
        ),
    )

    usage = response.usage_metadata
    log.info(
        "gemini_call",
        rti_type=rti_type.slug,
        source=source,
        model=settings.gemini_model,
        input_tokens=getattr(usage, "prompt_token_count", None),
        output_tokens=getattr(usage, "candidates_token_count", None),
    )

    if response.text is None:
        raise RuntimeError("Gemini returned no text")
    return answers_model.model_validate_json(response.text)


def extract_from_text(rti_type: RtiTypeDef, text: str) -> BaseModel:
    """For documents whose words are already in the file."""
    contents: list[Any] = [build_prompt(rti_type), "--- DOCUMENT TEXT ---", text]
    return _generate(rti_type, contents, source="text")


def extract_from_images(rti_type: RtiTypeDef, image_paths: list[Path]) -> BaseModel:
    """For scans - one picture per page, in page order."""
    pages: list[Any] = [
        types.Part.from_bytes(data=path.read_bytes(), mime_type="image/png") for path in image_paths
    ]
    contents: list[Any] = [build_prompt(rti_type), "--- DOCUMENT PAGES, IN ORDER ---", *pages]
    return _generate(rti_type, contents, source=f"images:{len(pages)}")
