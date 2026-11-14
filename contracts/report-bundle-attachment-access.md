# Copied report bundle byte-delivery permission

A report-output ZIP contains complete report and audit data. Explicitly registering
that file as opaque evidence must not make its bytes available under the weaker
ordinary evidence/testimony gate. Both POST evidence-intakes/{digest}:download and
GET evidence/{evidenceId}/content now apply this conservative content gate before
returning bytes or recording a successful Access event.

Any bytes beginning `PK` (including damaged/truncated ZIP headers), or recognized
by Python zipfile.is_zipfile via the ZIP end record (including prefixed ZIP files),
require reports.access.require_content: investigation role, every category explicit
ReadOnly/ReadWrite and no applicable field rule. No ZIP member is listed, extracted,
decompressed, rendered, fetched or executed. Filename, title, category, and file
extension never select or waive the gate. This includes ZIP-based DOCX and unrelated
ZIP containers; intentional compatibility tightening avoids trusting caller labels.

Both live endpoints acquire WRITE_LOCK then BEGIN IMMEDIATE before policy/source
reads; classification and full-content check share the reserved transaction with
the success audit. Existing original metadata/hash checks remain as before. Denied
requests return403/no-store and do not append Access. Historical restored evidence
already requires the same full-content permission and remains unchanged.

Registration is still an explicit opaque-file operation with its existing8MiB cap.
It does not certify origin, content, authenticity or permission to publish. Generated
bundles may be up to19MiB; those above8MiB cannot use this intake and are not silently
split/truncated. No automatic retention, reportId binding or new archive format.
Malformed or intentionally transformed content not recognized as ZIP is outside this
narrow guard. This is not general content classification/DLP and cannot detect report
text copied into plain text, PDF, another container format, or deliberately damaged
prefixed archives. Existing non-ZIP evidence behavior is unchanged; full source-policy
closure and production authenticated identity are not added by this fix.
