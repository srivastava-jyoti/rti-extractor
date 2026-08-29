"""One record per RTI type. Everything type-specific lives here, not in code.

Adding an RTI type means adding a definition below. The prompt, the answer schema, the
CMS payload mapping and the review screen labels are all generated from it at runtime.
"""

from dataclasses import dataclass
from enum import StrEnum

COUNT_WORDS = {
    1: "one",
    2: "two",
    3: "three",
    4: "four",
    5: "five",
    6: "six",
    7: "seven",
    8: "eight",
    9: "nine",
    10: "ten",
    11: "eleven",
    12: "twelve",
}


class AnswerType(StrEnum):
    """What kind of value a question expects."""

    NUMBER = "number"
    TEXT = "text"


@dataclass(frozen=True)
class FieldDef:
    name: str
    """The field name in the CMS. Used verbatim in the payload."""

    question: str
    """The question as asked, phrased for the model."""

    label: str
    """The short heading shown to the reviewer."""

    answer_type: AnswerType = AnswerType.NUMBER


@dataclass(frozen=True)
class RtiTypeDef:
    slug: str
    """Identifier for this type, matching the CMS singular name."""

    collection: str
    """The CMS collection, as it appears in the API path."""

    subject: str
    """What the request was about, used in the prompt's opening sentence."""

    multi_record: bool
    """True when one document yields one record per institution rather than one overall."""

    fields: tuple[FieldDef, ...]

    extra_rules: tuple[str, ...] = ()
    """Extraction rules that apply only to this type, already wrapped for the prompt."""

    @property
    def singular(self) -> str:
        return self.collection[:-1] if self.collection.endswith("s") else self.collection

    @property
    def api_uid(self) -> str:
        """The CMS content-type identifier, used in admin URLs."""
        return f"api::{self.singular}.{self.singular}"

    @property
    def relation_field(self) -> str:
        """The field on the parent RTI record that points back at this type."""
        return self.singular.replace("-", "_")

    @property
    def model_name(self) -> str:
        return "".join(part.capitalize() for part in self.slug.split("-")) + "Answers"

    @property
    def count_word(self) -> str:
        return COUNT_WORDS.get(len(self.fields), str(len(self.fields)))

    @property
    def labels(self) -> dict[str, str]:
        """Field name to numbered heading, for the review screen."""
        return {f.name: f"{i}. {f.label}" for i, f in enumerate(self.fields, start=1)}


BUDGET_RTI = RtiTypeDef(
    slug="budget-rti",
    collection="budget-rtis",
    subject="prison budgets",
    multi_record=False,
    fields=(
        FieldDef(
            name="annual_budget_for_prisons",
            question="the total annual budget for prisons for the financial year",
            label="Total annual budget for prisons",
        ),
        FieldDef(
            name="break_up_for_budget",
            question="the major heads or break-up of that total annual budget",
            label="Major heads / break-up of that total",
        ),
        FieldDef(
            name="sanctioned_individual_cost",
            question="the sanctioned cost of each prisoner, per month",
            label="Sanctioned cost per prisoner, per month",
        ),
        FieldDef(
            name="annual_individual_cost_sanctioned",
            question="the sanctioned cost of each prisoner, per year",
            label="Sanctioned cost per prisoner, per year",
        ),
        FieldDef(
            name="incurred_individual_cost",
            question="the actual incurred cost of each prisoner, per month",
            label="Incurred cost per prisoner, per month",
        ),
        FieldDef(
            name="annual_individual_cost_incurred",
            question="the actual incurred cost of each prisoner, per year",
            label="Incurred cost per prisoner, per year",
        ),
    ),
    extra_rules=(
        "- For the break-up question, put the printed total in number and the full itemised\n"
        "  text in other_specify.",
    ),
)

REGISTRY: dict[str, RtiTypeDef] = {BUDGET_RTI.slug: BUDGET_RTI}


def get_rti_type(slug: str) -> RtiTypeDef:
    try:
        return REGISTRY[slug]
    except KeyError:
        known = ", ".join(sorted(REGISTRY))
        raise KeyError(f"unknown RTI type {slug!r}; known types: {known}") from None
