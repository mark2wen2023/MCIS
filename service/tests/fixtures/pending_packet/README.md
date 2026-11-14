# Fixed public-report consistency fixture (not authentication)

This is the corrected, text-reviewed pending packet from the public Shanghai MSA report:
https://www.sh.msa.gov.cn/u/cms/www/202505/191445221747637122775.pdf

PDF SHA256: 99084b8e672da6e2f8d9809bea25a92fe5fcf31c318554832e14339610015d7f
PDF page 24, printed page 22; section 七 / （四）结论。

Only the single selected paragraph, the one-page extracted text required for the page hash,
and the pending packet's provenance/review metadata are packaged. No PDF, images, full report,
credentials, local filesystem path, or case database is included. Repeated text fields belong to
bindings that tests must check. Title/applicability labels are editorial, not report quotations.

The packet is retained byte-for-byte from the reviewed corrected artifact. Do not shorten the page
text and pretend its old page hash still applies. No automatic downloading or missing-file skip.
Run tests from service with installed project test dependencies:
python -m pytest -q tests/test_pending_packet_mapping.py tests/test_pending_packet_mapping_independent.py

The source label, saved URL and all hashes are test inputs, not verified publisher authority,
public status, usage rights or admission permission. The validator does not fetch the PDF or
re-establish extraction/visual review. All review/approval states remain pending; map_packet always
returns admissionAllowed=false. Self-consistent invented source hashes are explicitly tested as
untrusted. These are deterministic consistency tests, not OCR/LLM/SSO/production acceptance.
