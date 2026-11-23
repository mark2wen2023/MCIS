# Fixed-render local OCR receipt intake (synthetic controls only)

Parent 0ea4b0f1e77ab757ceab12d79b6838ddadffcaa7. Only a new research directory. No models, downloads, OCR execution, service import, routes, real documents or production storage.

## Reuse and limits
Inspected 91962113bd98778d3538f0e8e9879a014023c21f image_review/tasks.py, ppocr.py and contract notes. Reuses only the familiar parallel rec_texts/rec_scores/rec_boxes/rec_polys and page_index representation. Does not import its converter or produce its production candidate schema: that converter assumes rendered-page coordinates and a local OCR origin, inappropriate for these handwritten crop/rotation controls. Public-sample task and routes remain unchanged.

## Run
From candidate checkout, with the exact PDF/PNGs from the parent (instructions in research/synthetic_ocr_page_preflight/README.md):

    python -I -B research/synthetic_ocr_receipt/check.py --inputs /path/to/pinned-inputs
    python -I -B research/synthetic_ocr_receipt/intake.py --inputs /path/to/pinned-inputs --receipt-dir research/synthetic_ocr_receipt/controls

Eight tests pass, exit 0, including subprocess CLI roundtrip. The second command also actually ran, exit 0; control-receipt.json records stdout. Runtime paths in this example are operator-selected local roots. Payloads cannot select source paths: only synthetic.pdf and the two frozen PNG names are read. The independently frozen annotations file is inherited, not copied, and verified against SHA-256 82e5fa018c35c74dde104540edba140fbb410626a3c4526e7e156c0554e20a5a. An optional --annotations path accepts only identical bytes, for exported local tests. CLI prints a receipt and does not persist it or modify inputs. No source/path is taken from raw output.

## Receipt behavior
PDF and exact physical-page image bytes must match the inherited whitelist, including image dimensions. Raw bytes are bound by rawSha256 plus explicit self-made-ppocr-shaped/v1 schema; unknown versions, duplicate JSON keys, malformed array lengths, polygon order/bounds, mismatching box and polygon, wrong page and response source paths reject. Raw page_index=null and absent model confidence represented by null remain explicitly missing; not_run and missing run states remain separate and produce no lines or scores. An actual model-output mode is intentionally unsupported.

The checked-in controls are self-made text/polygon arrays, not real engine output. The crop is [132,588,199,694] in original PNG coordinates (67x106), hypothetically rotated clockwise 90 degrees to 106x67. A trusted test-host whitelist allows identity or this exact page-2 transform. Its inverse is original x=candidate y+132, original y=694-candidate x. Four corners map to the earlier visible-control polygon; no image crop/rotation operation or OCR preprocessing was executed. inverseVerified means this narrow test-host arithmetic whitelist, not an authenticated preprocessing receipt or professional verification. The internal verified=False case proves missing trust fails closed. Altered crop/rotation/size has no originalRasterPolygon or cell assignment. Future actual processing receipts need separately established host provenance.

Literal word equality, physical-page identity and raster-cell containment are separate fields. A different word in the same polygon changes textMatches, not geometric cell assignment. Reference cells/words are inherited frozen developer annotations, not independent expert labels. PDF precision remains page and originalPdfPolygon=null: this candidate has no trusted PNG-to-PDF inverse. All receipts have ocrRun=false, scores=null, confirmed=false and productionImportSupported=false. A model_score numeric value, if supplied, would remain explicitly self-made control data, never a measured model result.

Remaining validation: actual approved OCR output/version adapters, real preprocessing-chain provenance, independent transcription/semantic review and authenticated original access. No claim of OCR accuracy, arbitrary-document support, formal authorization, production readiness or professional judgment.
