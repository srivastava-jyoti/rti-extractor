# Architecture

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

## What happens on upload

**1. The file arrives.** The PDF is posted to `/extract` and read into memory. A SHA-256
fingerprint of its bytes becomes the filename it is stored under. The same document
uploaded twice occupies the same path. The fingerprint is also safe to put in a URL, which
is how the scan is served back to the reviewer.

**2. The PDF is inspected.** One pass with PyMuPDF collects, per page, the text, the
rotation flag, the page size and the bounding boxes of any images. Classification applies
in order:

```
total characters <= 100 x page count      ->  NONE    (no usable text)
otherwise, any image covering >60% of a
        page's area                       ->  OCR     (text present, but from a scan)
otherwise                                 ->  NATIVE  (real digital text)
```

The character floor exists because scans often carry a stray watermark or page number.
Treating that as text would skip extraction on a document nobody can read.

**3. The target record is looked up.** The uploaded filename is used to find where the scan
already belongs. The extension is stripped and the stem is sent as a filter on the CMS's
attached-media field. The CMS stores a sanitised version of every uploaded filename, and
files downloaded from it carry exactly that name, so this is an exact match. If the stem
finds nothing, the original filename is tried. One request returns the record, its
identifying fields, and whether it already has an entry of this type.

**4. Extraction.** NATIVE documents have their page text joined and sent as text. OCR and
NONE documents have every page rendered to PNG at 200 DPI and sent as images in page order.
A page image costs roughly 1,100 tokens. A short text document costs under a thousand in
total. Either way the request carries the instructions, the content, the schema as a
generation constraint, and `temperature=0`.

Transient failures, meaning upstream overload and rate limiting, are retried with increasing
waits up to five attempts. Anything else fails immediately, because a bad key or a wrong
model identifier will not succeed on retry. Token counts are logged on every call. The
response is validated locally against the same schema before it goes further.

**5. The review screen.** Six cards, each with an editable value, status and free-text
field. Beneath each one sits the page number, the unit as printed, and the verbatim
snippet. Two hidden fields travel with the form: the document fingerprint, and the target
record ID. The record ID is included only when that record has no entry yet. Nothing is
persisted at this stage. The extracted values live in the form itself.

**6. Saving.** Each value is cleaned. Separators and currency prefixes are stripped, and the
result is converted to a number or left empty if it will not convert. The status is mapped
to the exact string the CMS expects. The payload is assembled with the publish timestamp set
to null, plus the record ID when present. If `DRY_RUN` is on, the payload is logged and
nothing is sent. Otherwise one request creates the entry and returns its identifier, which
becomes the link on the confirmation screen.

A one-page scan takes about nine seconds end to end, most of it the model call. Longer
documents scale roughly with page count.

## Two structural guarantees

These are properties of the code path, not checks that could be forgotten.

The publish timestamp is always null, so nothing can be published. The record ID is absent
whenever linking would displace an existing entry, so nothing can be detached.
