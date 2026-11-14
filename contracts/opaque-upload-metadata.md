# Opaque upload metadata and registration-step status

The existing digital-file intake remains an opaque-byte preservation workflow. Photo,
Document, VDR and other categories are caller declarations, not validated media types.
File extension/browser MIME cannot establish actual type, safety, parsing success or
facts. No media decoder, OCR, ASR, image inference, inline rendering or automatic
metadata extraction is introduced.

New preview/commit inputs refuse filenames containing Unicode bidi controls U+061C,
U+200E/F, U+202A..E, U+2066..9 with422 INTAKE_FILENAME_DIRECTION. Existing filename,
byte and body budgets remain. Reject without rewriting or reflecting the filename.
The client applies the same rule before constructing a new intake request.
Historic metadata()/preview binding validation is unchanged so old registered names
remain readable/exportable; no silent migration/rename or authenticity claim. New
replay POSTs with such names are rejected; existing read-only receipt recovery still
works. Client parseReceipt keeps legacy filename validation for that purpose.

A new disclosure beside the selected file-intake evidence states: file copy registered,
category is human-declared, actual type unverified, and this registration step did not
perform OCR/ASR/visual/audio/video parsing. Hash status is separate and not content
understanding or authenticity. Show it only for same-case evidence with the exact
raw/evidence-intakes/<64-lowercase-hex>/source.bin path. This path indicates the known
workflow, not independent verification of a live receipt. No claims about later
analyses in other modules; ordinary/imported non-intake paths get no inferred status.
No additional network, file reads, state persistence, permissions or timeline behavior.
