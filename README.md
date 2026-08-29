# RTI Extractor

Reads scanned government Right to Information replies and turns them into structured,
reviewable draft entries in a Strapi CMS.

## The problem

An Indian NGO publishes prison data obtained through Right to Information (RTI) requests.
It files a standard set of questions with prison departments across the country; each
department replies by post or email with a scanned document. The replies arrive as
photocopies of typed pages, pages rotated inside an upright PDF, 1-bit black-and-white
scans with no greyscale left, and occasionally clean digital documents. Quality varies by
state and by office.

Until now, every reply was transcribed by hand. A person opened the scan, found each
answer, decided whether it counted as a real value or a refusal, and typed it into the CMS
one field at a time. The same work repeated for every reply received, for every question
set, across thirty question sets and thousands of documents. The transcription is also
where inconsistency entered the data: two people looking at the same qualified figure —
"Rs. 19,800 (Minimum)" — recorded it differently, and nothing in the CMS captured which
convention had been applied.

## What it does now

1. A reviewer uploads one scanned reply.
2. The system classifies the PDF: real digital text, unreliable OCR text, or pure scan.
3. It reads the answers — from the document's own text where that is trustworthy,
   otherwise from rendered page images via a vision model.
4. It looks up which RTI record that scan already belongs to in the CMS.
5. It shows every answer alongside the page number and the verbatim text it was read from.
6. The reviewer corrects anything wrong and saves.
7. An **unpublished draft** is created in the CMS, linked to the correct RTI record.

The reviewer then opens the draft in the CMS and publishes it.

**The system never publishes.** Every entry it creates is a draft. **It never overwrites or
detaches existing data**: if the target record already has an entry, the tool refuses to
link and says so, rather than silently reassigning the relation.

<!-- SCREENSHOT: review screen — the six answers with their source snippets, and the
     matched-record banner above them. Place a PNG or GIF at docs/review-screen.png -->

## Design decisions

### Three-way document classification, not a boolean text-layer check

The obvious approach is to ask "does this PDF contain text?" and read it directly if so.
That check is wrong, and the failure is silent.

One reply in the corpus carried a text layer that looked entirely valid — over two thousand
characters, well above any sensible threshold. It was OCR output someone had baked into a
scan years earlier, and it was wrong: it rendered "information" as `informatton` and mangled
a proper name. Misspelled words are visible and harmless. A misread digit is not: `19677`
and `19577` look equally plausible, and the number in question was a state's annual prison
budget. Nothing in the file records which characters the OCR was confident about.

So the classifier distinguishes three cases. **NATIVE** — text produced by a word processor,
exact, read it directly at no cost. **OCR** — text present but derived from a scan, therefore
untrusted; ignore it and read the images instead. **NONE** — no text, read the images.

The signal that separates NATIVE from OCR is whether a single image covers most of the page.
A genuinely typed document has no photograph of itself inside it; a full-page image sitting
behind a text layer is the fingerprint of a scan someone has run OCR over.

### Schema-constrained generation, not prompt-and-parse

The model is not asked to return JSON and then parsed. The answer schema is supplied to the
API as a structured-output constraint, so the response is generated against the schema
rather than merely encouraged to match it. The result is then validated a second time
locally before anything is written.

Prompt-and-parse fails in ways that are tedious and unbounded: prose wrapped around the
JSON, a missing field, a number returned as `"approximately 450"`. Each becomes a parser
special case. Constraining generation removes the class of failure instead of handling its
instances, and the local validation means a malformed response fails loudly at the boundary
rather than reaching the CMS.

### Per-field provenance: page number, verbatim snippet, unit as printed

Every extracted answer carries where it came from and the exact text it was read from.

Review is not possible without this. A reviewer shown a bare number has two options: trust
it, or open the PDF and search for it. The first defeats the purpose and the second is
slower than transcribing by hand. Shown the number next to the sentence it came from, they
can confirm or reject it in seconds. The provenance is what converts the reviewer's job from
transcription to verification.

The unit field exists for a specific hazard. One reply states a figure with a header reading
"Rupees in lac"; another states a figure in plain rupees. Stored as bare numbers they differ
by a factor of a hundred thousand with nothing recording why. The system records the unit as
printed and does not reconcile it — the discrepancy surfaces in review rather than settling
silently into the data.

### The model may not calculate, convert, or infer

Three explicit prohibitions, each preventing a different failure.

**No calculation.** Where a reply lists component amounts but no total, the total is left
empty. A computed total is indistinguishable in the database from a printed one, and a
reviewer has no way to tell that a figure was never in the document. In testing, a document
gave a per-day cost against a question asking for a monthly cost; multiplying by thirty
would have been trivial and wrong.

**No unit conversion.** Converting "in lakh" to rupees requires assuming the header applies
to that row, which is an inference about layout, not a reading of the page.

**No inference of missing values.** An unanswered question is recorded as unanswered. The
schema distinguishes four states — a value, "the department stated the data is
unavailable", "the question was not answered at all", and "an answer was given but is not a
single figure". Collapsing these loses information that cannot be recovered later, and the
CMS itself already models the distinction.

### Drafts, with a human approving

Nothing the system produces is publicly visible. Entries are created unpublished and are
invisible to the CMS's public API until a person publishes them.

This is not caution for its own sake. The output is published as fact about public
institutions, and the failure mode of an extraction system is not a crash — it is a
plausible wrong number that nobody notices. A human approval step is the only control that
catches that, and it is cheap because the provenance makes each check take seconds.

### Why this is extraction, not retrieval-augmented generation

RAG solves the problem of finding relevant material in a corpus too large to read. That
problem does not exist here. The document is given — the reviewer just uploaded it — and it
fits comfortably in the model's context, so there is nothing to retrieve.

Adding retrieval would add a failure mode rather than remove one: a chunker that drops the
page containing the answer produces a confident "not found" with no indication anything was
missed. It would also destroy the structure the answers live in. These replies are tables,
and a table's meaning depends on row and column alignment; chunking text linearly separates
a figure from the row label that gives it meaning. Sending whole pages as images preserves
the layout the model needs to read them correctly.

## Corpus findings

The design above came from examining real documents before writing extraction code. The
findings changed several assumptions.

**Three document types where one was expected.** The working assumption was that every reply
is a scan. Of an initial sample, most were, but one was a digital document whose answers
could be read exactly and free, and one was a scan carrying misleading OCR text. Each needs
different handling.

**Scan quality varies more than expected.** Rendered page resolution across the sample ran
from roughly 139 to 531 DPI. The low end is below where small marks begin to break up. One
document was 1-bit black and white — the scanner had already discarded every intermediate
tone before the file was created, so no amount of processing can recover a faint digit.

**Rotation metadata is unreliable.** One document's pages display correctly but the image
stored inside them is rotated ninety degrees. Another has content that runs sideways within
pages that are upright and correctly proportioned. In both cases the PDF's own rotation flag
reads zero. Neither the metadata nor the page aspect ratio detects the problem — only
rendering the page and looking at it does.

That last finding removed work rather than adding it: because the renderer applies each
page's display transform, pages come out upright for every document in the target set, and a
planned orientation-correction stage was dropped as unnecessary. It would have been built on
an assumption that the metadata was meaningful.

## Accuracy

Thirty of thirty fields were correct across five documents, verified by hand against the
original scans. This included an eight-digit figure read from a photocopy, and, in three
separate documents, itemised component amounts that summed exactly to the totals stated
elsewhere in the same reply — an arithmetic cross-check that fails if any single digit is
misread.

**This is a signal, not a measured accuracy rate.** Five documents hand-checked by the
author is not an evaluation. The next step is a comparison against the existing verified
entries already in the CMS, which are effectively free labelled data: run those documents
through the pipeline and compare field by field at a scale where a rate means something. No
percentage is claimed until that exists.

One caveat that measurement will have to account for: the existing entries were transcribed
by different people using different conventions, so disagreement with them will not always
indicate an extraction error.

## Architecture

```
    upload
      |
      v
  +--------------------------------------+
  |  classify: NATIVE / OCR / NONE       |
  +--------------------------------------+
      |                          |
   NATIVE                   OCR or NONE
      |                          |
      v                          v
  read text                render pages to images
      |                          |
      +------------+-------------+
                   |
                   v
      +-------------------------------+
      |  schema-constrained model call |
      |  -> answers + provenance       |
      +-------------------------------+
                   |
                   v
      +-------------------------------+
      |  look up the target CMS record |
      |  by the file's stored name     |
      +-------------------------------+
                   |
                   v
             review screen
        (values, page, snippet, unit)
                   |
              human edits
                   |
                   v
        unpublished draft in the CMS
                   |
           human publishes
```

| Module | Responsibility |
| --- | --- |
| `pdf/reader.py` | Open a PDF, classify its text layer, render pages to images, fingerprint the file |
| `extract/schema.py` | The answer shape: value, status, free text, page, snippet, unit |
| `extract/prompts.py` | The extraction instructions, including the prohibitions above |
| `extract/client.py` | The model call, structured-output constraint, token accounting, retry on transient failures |
| `strapi/client.py` | Find the target CMS record, map answers to the CMS payload, create the draft |
| `web/app.py` | Upload, review and confirmation screens; serves the uploaded scan back for checking |

## Stack

- **Python 3.12** — pinned below 3.13 because the imaging and PDF libraries lag new releases.
- **uv** — dependency resolution and a lockfile, so CI and the server install byte-identical versions.
- **FastAPI + Jinja templates** — server-rendered pages; the review screen is a form, not an application.
- **PyMuPDF** — page counting, text extraction and rendering from one library rather than three.
- **Pydantic / pydantic-settings** — the answer schema and typed configuration validated at startup.
- **structlog** — answers are logged with the document fingerprint and page, so a query about one entry is answerable after the fact.
- **tenacity** — retries only transient failures (rate limits, upstream overload) and fails fast on everything else.
- **Strapi v4** — the client's existing CMS; not a choice made here.

## Known limitations

- One question set of roughly thirty is implemented. The rest vary substantially in shape; some produce one record per document, others many.
- Hindi and other non-Latin scripts are deferred. The documents exist in the corpus and are the hardest cases: Devanagari on a 1-bit photocopy, with content rotated within the page.
- Documents below roughly 150 DPI are unreliable and the system does not currently warn about it.
- There is no automated evaluation harness. Accuracy has been established by hand on a small sample.
- The tool creates the answer record but does not create the parent RTI record or attach the scan; both already exist in the client's workflow.

## Roadmap

1. **Evaluation against existing verified entries.** Compare pipeline output with entries already transcribed by hand, per field, to produce a defensible accuracy figure and identify which fields are safe to pre-fill.
2. **Schema generation at runtime.** Read the field definitions and question wording from the CMS rather than hardcoding them, so a new question set is configuration rather than code.
3. **Multi-record documents.** Some replies answer for many institutions in one table, producing many records from one file. This needs list output, joining across several tables in the same document, and a table-based review screen.
4. **Automated evaluation harness.** Ground-truth fixtures and a diff between runs, so a prompt change can be judged by measurement rather than by eye.

## Setup

Requires [uv](https://docs.astral.sh/uv/) and a reachable Strapi v4 instance.

```bash
git clone <repository-url>
cd rti-extract
uv sync
```

Copy the example configuration and fill it in:

```bash
cp .env.example .env
```

| Variable | Purpose |
| --- | --- |
| `GEMINI_API_KEY` | API key for the vision model |
| `GEMINI_MODEL` | Model identifier, for example a Gemini Flash model |
| `STRAPI_BASE_URL` | CMS API root, for example `http://localhost:1337/api` |
| `STRAPI_API_TOKEN` | CMS token with create permission on the target collection |
| `DATABASE_URL` | Currently required by configuration validation but unused |
| `WORK_DIR` | Where rendered pages and uploads are written. Default `./data/work` |
| `LOG_LEVEL` | Default `INFO` |
| `DRY_RUN` | Defaults to `true`. When true the CMS payload is logged and nothing is written |

`DRY_RUN` defaults to on. Leave it on for the first run, read the logged payload, and only
then set it to `false`.

Run the application:

```bash
uv run uvicorn rti_extractor.web.app:app --port 8017
```

Open `http://localhost:8017`.

Inspect a PDF without running extraction:

```bash
uv run python scripts/inspect_pdf.py /path/to/file.pdf
uv run python scripts/inspect_pdf.py --render /path/to/file.pdf
```

Run one document through extraction from the command line:

```bash
uv run python scripts/extract_pdf.py /path/to/file.pdf
```

## Development

```bash
uv run ruff check .
uv run ruff format .
uv run mypy src
uv run pytest
```

CI runs all four on every push. `mypy` is configured in strict mode for `src`.

Real reply documents contain personal data and must not be committed. `.gitignore` blocks
`*.pdf`, `*.png`, `*.jpg` and `data/`, and pre-commit hooks reject large files and private
keys. Test documents belong outside the repository.
