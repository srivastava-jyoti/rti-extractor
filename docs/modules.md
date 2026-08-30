# Modules

| Module | Responsibility |
| --- | --- |
| `rti_type.py` | One config record per RTI type: collection, single-or-multi-record flag, and the fields with their CMS name, question wording and answer type |
| `config.py` | Settings, read from `.env` and validated at startup |
| `logging.py` | Structured logging setup, used everywhere else |
| `pdf/reader.py` | Open a PDF, classify its text layer, render pages to images, fingerprint the file |
| `extract/schema.py` | The answer shape, and building the answer model for a type from its config |
| `extract/prompts.py` | Assembling the extraction instructions from the config |
| `extract/client.py` | The model call, schema constraint, token accounting, retry on transient failures |
| `strapi/client.py` | Find the target CMS record, map answers to the CMS payload, create the draft |
| `web/app.py` | Upload, review and confirmation screens, and serving the uploaded scan back |

## Scripts

| Script | Purpose |
| --- | --- |
| `scripts/inspect_pdf.py` | Report page count, text-layer verdict, rotation and fingerprint. Optionally render pages |
| `scripts/hello_gemini.py` | List the models the API key can reach. Written to prove the key works before anything depended on it |
| `scripts/extract_pdf.py` | Run one document through the pipeline from the command line |

## Empty packages

`cli/`, `db/`, `preprocess/` and `validate/` exist and are empty. They were the stages the
original plan expected. Two were dropped on evidence: rendered pages came out upright, so
orientation correction was unnecessary, and one-at-a-time upload needs no job queue. The
folders record what was planned and deliberately not built.
