EXTRACTION_PROMPT = """You are reading a reply from an Indian prison authority to a Right
to Information request about prison budgets.

Fill in the six answers using this document only.

The six questions that were asked:
1. annual_budget_for_prisons - the total annual budget for prisons for the financial year
2. break_up_for_budget - the major heads or break-up of that total annual budget
3. sanctioned_individual_cost - the sanctioned cost of each prisoner, per month
4. annual_individual_cost_sanctioned - the sanctioned cost of each prisoner, per year
5. incurred_individual_cost - the actual incurred cost of each prisoner, per month
6. annual_individual_cost_incurred - the actual incurred cost of each prisoner, per year

Replies often label their answers "Ans 1" to "Ans 6", or number rows 1 to 6 in a table.
These numbers refer to the six questions above, in that order. A reply that starts at
"Ans 3" has simply not answered questions 1 and 2.

Rules:
- Report only what is printed. Never infer, estimate, or work out a missing figure.
- Never add numbers together. If a break-up is printed with no total, leave number null.
- Copy the exact text you read into snippet, word for word.
- Give the 1-indexed page number you read each answer from.
- Put the unit exactly as printed into unit_as_printed, for example "Rupees in lac".
  Never convert between units.
- For number, give digits only - no commas, no currency symbol, no unit.
- Use status not_available when the reply says the data is unavailable or does not exist.
- Use status not_provided when the question is not answered anywhere in the document.
- Use status other when an answer is given but is not a single figure, and put that
  answer in other_specify.
- For the break-up question, put the printed total in number and the full itemised
  text in other_specify.
"""
