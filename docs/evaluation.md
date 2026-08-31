# Evaluation

## Method

The CMS already holds entries transcribed by hand. Those values are the ground truth. The
same source documents are run through the pipeline and compared field by field.

For each field, two things are compared:

- **the number** — a match means both are empty, or both are present and equal to two
  decimal places
- **the status** — our four internal states mapped onto the CMS enumeration
  (`available`, `not_available`, `not_provided`, `other`)

Free text is not scored. It is prose, and the pipeline now writes it in English while the
source may be in another language, so a verbatim comparison would produce a meaningless
figure.

No document in the evaluation set was used while developing the prompt.

## Results

Sixteen documents, ninety-six fields.

| Field | n | Number | Status | Both |
| --- | --- | --- | --- | --- |
| Total annual budget | 16 | 100.0% | 93.8% | 93.8% |
| Break-up of that total | 16 | 93.8% | 87.5% | 81.2% |
| Sanctioned cost per month | 16 | 87.5% | 50.0% | 50.0% |
| Sanctioned cost per year | 16 | 93.8% | 56.2% | 50.0% |
| Incurred cost per month | 16 | 100.0% | 62.5% | 62.5% |
| Incurred cost per year | 16 | 100.0% | 56.2% | 56.2% |
| **All** | **96** | **95.8%** | **67.7%** | **65.6%** |

## Reading the status column

There were 31 disagreements in total. **Twenty-four of them are the same one**: the human
recorded `other` where the pipeline recorded `not_available`.

Both read the page identically. They labelled it differently, on replies of the form "no
per-prisoner budget is sanctioned". That is a house-style question rather than a reading
error, and settling it would move the status column substantially.

The remaining seven disagreements are one-offs, in both directions, including one field the
human left unset.

This is also why the number column is the more meaningful measure. It reflects whether the
document was read correctly. The status column additionally reflects whether two people would
have classified the same answer the same way, and the ground truth itself is not internally
consistent on that: entries in the CMS were transcribed by different people using different
conventions.

## Why sixteen and not the full set

The evaluation set is 103 documents. The run stopped at 16 because of an API quota:

```
quotaId    : GenerateRequestsPerDayPerProjectPerModel-FreeTier
quotaValue : 20
```

Twenty requests per day, per model, on the free tier. The run is resumable and skips
documents that have already completed, so it continues from where it stopped without
repeating work.

## Separately: hand-checking against the original scans

Before this evaluation, six documents were checked field by field against the original scans
rather than against the CMS. All thirty-six fields were correct. That included a ten-digit
figure where the digits, the same amount written out in words beside them, and a separate
page stating it in different units all agreed. In three of those documents, itemised
components summed exactly to totals stated elsewhere in the same reply.

Two further documents are findings rather than scores. One contained none of the requested
figures, having answered by attaching raw budget reports, and every field was correctly
reported as not provided. One answers for around thirty institutions in a single table, which
the current single-record schema cannot represent, and no value was invented to fill the gap.
