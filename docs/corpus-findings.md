# Corpus findings

The design came from examining real documents before writing extraction code. The findings
changed several assumptions.

## Three document types where one was expected

The working assumption was that every reply is a scan. Most were. One was a digital document
whose answers could be read exactly and at no cost. One was a scan carrying OCR text that
looked valid and was wrong: it rendered "information" as `informatton` and mangled a proper
name. Each of the three needs different handling, and the third is the dangerous one,
because a character count alone would have accepted it.

## Scan quality varies more than expected

Rendered page resolution across the sample ran from roughly 139 to 531 DPI. The low end sits
below where small marks begin to break up. One document was 1-bit black and white. The
scanner had discarded every intermediate tone before the file was created, so no processing
can recover a faint digit.

## Rotation metadata is unreliable

One document's pages display correctly, but the image stored inside them is rotated ninety
degrees. Another has content running sideways within pages that are upright and correctly
proportioned. In both cases the PDF's own rotation flag reads zero. Neither the metadata nor
the page aspect ratio detects the problem. Only rendering the page and looking at it does.

That finding removed work rather than adding it. Because the renderer applies each page's
display transform, pages come out upright for every document in the target set. A planned
orientation-correction stage was dropped as unnecessary. It would have been built on the
assumption that the metadata meant something.

## Replies do not always answer the questions

One reply consists of a covering letter and ten pages of raw budget reports from a state
financial system. It contains allotted and surrendered amounts per object head. It contains
no total annual budget and no per-prisoner cost. The requested figures were never written
down.

This was tested directly. The model read the Devanagari column on a rotated 1-bit page
correctly, transcribed eleven terms without translating them, and identified the report type
and financial year. Resolution, script and rotation were all ruled out. The document simply
does not answer the questions, and reporting the fields as not provided was correct.

That case is the reason for the prohibition on calculating. The ten per-head totals could
have been summed into a plausible answer that appeared nowhere in the document.
