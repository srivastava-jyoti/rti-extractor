from enum import StrEnum
from functools import lru_cache
from typing import Any

from pydantic import BaseModel, Field, create_model

from ..rti_type import AnswerType, RtiTypeDef


class DataStatus(StrEnum):
    AVAILABLE = "available"
    NOT_AVAILABLE = "not_available"
    NOT_PROVIDED = "not_provided"
    OTHER = "other"


class Answer(BaseModel):
    number: float | None = Field(
        default=None,
        description="The figure exactly as printed, digits only. Null if no figure is given.",
    )
    status: DataStatus = Field(
        description=(
            "available: a figure or answer is given. "
            "not_available: the reply says the data is not available or does not exist. "
            "not_provided: the question is simply unanswered in this document. "
            "other: an answer is given but it is not a single figure."
        )
    )
    other_specify: str | None = Field(
        default=None,
        description="Any answer that is not a single number, such as a break-up of amounts.",
    )
    page: int | None = Field(default=None, description="1-indexed page this was read from.")
    snippet: str | None = Field(
        default=None, description="The exact text read from the document, copied verbatim."
    )
    unit_as_printed: str | None = Field(
        default=None,
        description="The unit as printed, e.g. 'Rupees in lac'. Do not convert. Null if absent.",
    )


class TextAnswer(Answer):
    """For questions whose answer is words rather than a figure."""

    number: float | None = Field(
        default=None,
        description="Unused for this question. Put the answer in other_specify.",
    )


ANSWER_MODELS: dict[AnswerType, type[Answer]] = {
    AnswerType.NUMBER: Answer,
    AnswerType.TEXT: TextAnswer,
}


@lru_cache
def build_answers_model(rti_type: RtiTypeDef) -> type[BaseModel]:
    """Build the answer schema for one RTI type from its field definitions.

    One field per question, each holding the same value/status/provenance shape. Cached
    so the same class object is reused across calls.
    """
    definitions: dict[str, Any] = {
        field.name: (ANSWER_MODELS[field.answer_type], ...) for field in rti_type.fields
    }
    return create_model(rti_type.model_name, **definitions)
