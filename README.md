# RTI Extractor

Reads scanned government Right to Information replies and creates structured, reviewable
draft entries in a Strapi CMS.

> An independent experiment in applying vision-language extraction to scanned government
> documents. All collection names, field names and identifiers in this repository are
> generic examples, not those of any particular system. No real reply documents are
> included, and none should be: they contain personal data.

## The problem

Organisations that publish data obtained through Right to Information requests file a
standard set of questions with government departments. Each department replies with a
scanned document. The scans vary: photocopies, pages rotated inside an upright PDF, 1-bit
black-and-white with no greyscale left, and occasionally a clean digital file.

Until now a person opened each reply, found each answer, and typed it into the CMS field by
field. That work repeated across thirty question sets and thousands of documents.

## How it works

1. A reviewer uploads one scanned reply.
2. The system classifies it: real digital text, unreliable OCR text, or pure scan.
3. It reads the answers from the file's own text where that is exact, otherwise from
   rendered page images.
4. It finds the CMS record that scan already belongs to.
5. It shows each answer with its page number and the exact sentence it was read from.
6. The reviewer corrects anything wrong and saves.
7. An unpublished draft appears in the CMS. A person opens it and publishes.

The system never publishes. It never overwrites or detaches existing data. If the target
record already has an entry, it refuses to link and says so.

Depth on the pipeline: [architecture and request path](docs/architecture.md) and the
[module table](docs/modules.md).

<!-- SCREENSHOT: the review screen, showing the six answers with their source snippets and
     the matched-record banner. Place a PNG or GIF at docs/review-screen.png -->

## Techniques and stack

**Vision-language document extraction.** Rendered pages go to a multimodal model, so table
layout is preserved rather than flattened by OCR into a character stream.

**Schema-constrained generation.** The same machinery as function calling. The model is
given a typed signature and generation is constrained to satisfy it.

**Runtime schema generation.** The answer model is built from a config record rather than
written by hand, so a new question set is configuration rather than code.

**Provenance tracking with a four-state answer model.** Every answer carries its page
number, the verbatim snippet and the unit as printed. The status distinguishes a value from
three different kinds of absence.

No model was trained or fine-tuned. Accuracy comes from constraints, validation and
measurement, not from training.

**Stack**

- Python 3.12, pinned below 3.13 because the imaging and PDF libraries lag new releases
- uv, for a lockfile so CI and the server install identical versions
- FastAPI with Jinja templates, server-rendered; the review screen is a form
- PyMuPDF, for page counting, text extraction and rendering from one library
- Google Gemini via `google-genai`
- Pydantic and pydantic-settings, for the answer schema and typed configuration
- structlog, so a question about one document is answerable months later
- tenacity, retrying only rate limits and upstream overload
- Strapi v4 as the target CMS, chosen here because it models drafts and publishing directly

## Design decisions

### Three-way document classification

The obvious check is whether the PDF contains text, and read it directly if so. That fails
silently. One reply carried over two thousand characters of OCR text baked in years earlier,
which rendered "information" as `informatton`. A misspelled word is visible; a misread digit
in a budget figure is not. So a file is classified NATIVE, OCR or NONE, and OCR text is
discarded in favour of the page images.

### Schema-constrained generation

The obvious approach is to ask for JSON and parse it. That fails in unbounded ways: prose
wrapped around the JSON, a missing field, a number returned as `"approximately 450"`. Each
becomes a parser special case. Instead the schema is attached to the request as a generation
constraint, and the response is validated again locally before anything is written.

### Per-field provenance

The obvious output is a value per question. A reviewer shown a bare number can only trust it
or reopen the PDF, and the second is slower than transcribing by hand. So every answer
carries its page number and the exact sentence it came from. That turns the reviewer's job
from transcription into verification.

### The model may not calculate, convert or infer

The obvious behaviour is to be helpful and fill gaps. One reply consisted of a covering
letter and ten pages of raw budget reports, containing none of the figures the questions
asked for. Summing the ten per-head totals would have produced a plausible number that
appears nowhere in the document, and nothing downstream could tell it from a printed one.
The system reported those fields as not provided.

### Drafts, not published entries

The obvious step after extraction is to write the record. The failure mode here is not a
crash, it is a plausible wrong number that nobody notices, and the output is published as
fact about public institutions. So every entry is created unpublished and is invisible to
the CMS's public API until a person publishes it.

## Accuracy

Measured against entries already transcribed by hand in the CMS. Those values are the ground
truth; the same source documents are run through the pipeline and compared field by field.

**Sixteen documents, ninety-six fields. The numbers agreed 95.8% of the time.**

| Field | Number | Status |
| --- | --- | --- |
| Total annual budget | 100.0% | 93.8% |
| Break-up of that total | 93.8% | 87.5% |
| Sanctioned cost per month | 87.5% | 50.0% |
| Sanctioned cost per year | 93.8% | 56.2% |
| Incurred cost per month | 100.0% | 62.5% |
| Incurred cost per year | 100.0% | 56.2% |
| **All** | **95.8%** | **67.7%** |

The number column measures whether the document was read correctly. The status column also
measures whether two people would classify the same answer the same way, and there were 31
disagreements of which **24 are a single repeated pattern**: the human recorded `other` where
the pipeline recorded `not_available`, on replies meaning "no per-prisoner budget is
sanctioned". Both read the page identically. That is a house-style question, and the ground
truth is not internally consistent on it either, having been transcribed by different people.

The evaluation set is 103 documents. The run stopped at 16 on an API quota of twenty requests
per day on the free tier. It is resumable, and this figure will be replaced by the full one
when the rest have run.

Separately, six documents were checked by hand against the original scans rather than against
the CMS, and all thirty-six fields were correct. Two more are findings rather than scores: one
contained none of the requested figures and every field was correctly reported as not
provided; one answers for around thirty institutions in a single table that the current
single-record schema cannot represent, and no value was invented to fill the gap.

Full method and results: [evaluation](docs/evaluation.md). See also the
[corpus findings](docs/corpus-findings.md), which shaped the design, and the
[roadmap](docs/roadmap.md).

## Setup

Requires [uv](https://docs.astral.sh/uv/) and a reachable Strapi v4 instance.

```bash
git clone <repository-url>
cd rti-extract
uv sync
cp .env.example .env
```

Fill in `.env`:

| Variable | Purpose |
| --- | --- |
| `GEMINI_API_KEY` | API key for the vision model |
| `GEMINI_MODEL` | Model identifier |
| `STRAPI_BASE_URL` | CMS API root, for example `http://localhost:1337/api` |
| `STRAPI_API_TOKEN` | CMS token with create permission on the target collection |
| `WORK_DIR` | Where rendered pages and uploads are written. Default `./data/work` |
| `LOG_LEVEL` | Default `INFO` |
| `DRY_RUN` | Defaults to `true`. The payload is logged and nothing is written |

Leave `DRY_RUN` on for the first run, read the logged payload, then set it to `false`.

```bash
uv run uvicorn rti_extractor.web.app:app --port 8017
```

Open `http://localhost:8017`.

Command line, without the web app:

```bash
uv run python scripts/inspect_pdf.py /path/to/file.pdf     # classify and report
uv run python scripts/extract_pdf.py /path/to/file.pdf     # extract and print JSON
```

Checks, all four of which CI runs on every push:

```bash
uv run ruff check . && uv run ruff format . && uv run mypy src && uv run pytest
```

Real reply documents contain personal data and must not be committed. `.gitignore` blocks
`*.pdf`, `*.png`, `*.jpg` and `data/`. Pre-commit hooks reject large files and private keys.
Test documents belong outside the repository.
