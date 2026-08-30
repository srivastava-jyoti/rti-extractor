from ..rti_type import RtiTypeDef

SHARED_RULES = """\
- Report only what is printed. Never infer, estimate, or work out a missing figure.
- Never add numbers together. If a break-up is printed with no total, leave number null.
- Copy the exact text you read into snippet, word for word, in the script it is printed in.
  Never translate snippet.
- Write other_specify in English. If the reply is in another language, translate it there.
- Give the 1-indexed page number you read each answer from.
- Put the unit exactly as printed into unit_as_printed, for example "Rupees in lac".
  Never convert between units.
- For number, give digits only - no commas, no currency symbol, no unit.
- Use status not_available when the reply says the data is unavailable or does not exist.
- Use status not_provided when the question is not answered anywhere in the document.
- Use status other when an answer is given but is not a single figure, and put that
  answer in other_specify."""


def build_prompt(rti_type: RtiTypeDef) -> str:
    """Assemble the extraction instructions for one RTI type."""
    count = len(rti_type.fields)
    word = rti_type.count_word
    questions = "\n".join(
        f"{i}. {field.name} - {field.question}" for i, field in enumerate(rti_type.fields, start=1)
    )
    rules = "\n".join((SHARED_RULES, *rti_type.extra_rules))

    return f"""You are reading a reply from an Indian prison authority to a Right
to Information request about {rti_type.subject}.

Fill in the {word} answers using this document only.

The {word} questions that were asked:
{questions}

Replies often label their answers "Ans 1" to "Ans {count}", or number rows 1 to {count} in a table.
These numbers refer to the {word} questions above, in that order. A reply that starts at
"Ans 3" has simply not answered questions 1 and 2.

Rules:
{rules}
"""
