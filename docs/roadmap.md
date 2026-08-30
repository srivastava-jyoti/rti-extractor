# Roadmap

## 1. Evaluation against existing verified entries

The CMS already holds entries transcribed by hand. Run those documents through the pipeline
and compare field by field. That produces a defensible accuracy figure and shows which
fields are safe to pre-fill.

One caveat the measurement has to account for: those entries were transcribed by different
people using different conventions. Disagreement will not always mean an extraction error.
Those discrepancies are useful output in their own right, because they surface
inconsistencies in already-published data.

## 2. Schema generation from the CMS

The config record is already the single source of truth for an RTI type. The next step is to
read the field definitions and question wording from the CMS itself rather than writing the
config by hand. A new question set then becomes configuration rather than code.

## 3. Multi-record documents

Some replies answer for many institutions in one table, producing many records from one
file. One example runs to 39 pages covering around 30 institutions, with one row per
institution per statement table.

This needs list output, joining rows across several tables in the same document by
institution name, support for repeatable sub-blocks, and a table-based review screen instead
of one card per question. The `multi_record` flag in the config record exists for this and
is currently unused.

## 4. Automated evaluation harness

Ground-truth fixtures and a diff between runs, so a prompt change can be judged by
measurement rather than by eye.

## 5. Self-consistency verification

Numeric fields would be extracted twice in independent passes. Disagreement would set the
value aside and flag it for review rather than choosing between the two readings.

Confidence scores are the model's own self-report and are not calibrated against measured
error. Agreement between two independent passes is a stronger signal. This is the control
that catches a confident misreading in a misaligned table row.
