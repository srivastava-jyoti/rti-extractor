from enum import StrEnum

from pydantic import BaseModel, Field


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


class BudgetRtiAnswers(BaseModel):
    annual_budget_for_prisons: Answer
    break_up_for_budget: Answer
    sanctioned_individual_cost: Answer
    annual_individual_cost_sanctioned: Answer
    incurred_individual_cost: Answer
    annual_individual_cost_incurred: Answer
