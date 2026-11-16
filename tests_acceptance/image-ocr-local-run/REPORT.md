# Actual local PP-OCRv5 to isolated candidate — developer evidence

Parent e6d8936e78556bb49e78f6fae14daacef4489dab; default production app unchanged.
This round ACTUALLY ran installed PaddleOCR twice on the existing public page6 PNG,
not merely importing historical OCR. First direct trial succeeded; then the parameterized,
source-checked repository runner was executed successfully. Both raw results have identical
SHA256 44700324a56744044716e89a9f75b470cfb8566fa6cfc318b98602e9c0a3e9a5.

## Runtime and provenance
PaddlePaddle3.2.0 / PaddleOCR3.3.2 / PaddleX3.3.13; PP-OCRv5_mobile_det and
PP-OCRv5_mobile_rec; CPU4 threads, CUDA not compiled, MKLDNN disabled.
Cached tar hashes and all extracted model files matched recorded official downloads:
- det 50446e5d01ac2a73d5319c89513281f6578414c888c602f9af13f93feefffc58
- rec 566b9512b34e34a9f0db54d87b51fa5a0b9ed2cf1ab7e49728cc0b8b5a64f414
Prior official URLs are under https://paddle-model-ecology.bj.bcebos.com/paddlex/official_inference_model/paddle3.0.0/ (model-name_infer.tar).
No install/new model download, source-check-disable flag, API key or external OCR used.
Library initialization ran its normal model-hoster connectivity check: no hoster available.
It then used explicit pre-existing local model directories, supported by the installed library.
No network retry, source-check disabling or security-setting change. Before predict, a Python
audit guard rejects socket connect/DNS and subprocess attempts; none raised. This is not
OS-level packet capture/egress certification. Initialization connectivity requests contain no
sample data. Clean child environment/temporary HOME used, no credentials passed.

Public landing: https://www.sh.msa.gov.cn/sgdc/104170.jhtml
Previously obtained PDF SHA256:99084b8e672da6e2f8d9809bea25a92fe5fcf31c318554832e14339610015d7f.
Image SHA256:e097321c40047e305beb50f2676370f89a452ba49a11dc962ec4add9b6a70aff.
Manifest declares physical PDF6 / printed4; no new rendering/page mapping certification.
First init12.8517s / predict10.9629s. Repository runner init10.9098s / predict12.1664s.
Initialization includes connectivity/library work; not a production benchmark.

## Actual new code chain and results
`tools/image_review/run_public_page6.py`: explicitly invoked CLI, pinned public image,
pre-existing hash-checked local models, new output directory, actual raw.json and run.json.
`mcis_service.image_review.ppocr`: offline adapter of aligned PP-OCR arrays, validates raw
SHA, keeps blank/null/index/box/version fields, rejects unequal arrays/unsupported tables;
then calls existing candidate parser. Does not run OCR itself or certify provenance.
The server still labels its action `imported-existing-output`: the CLI ran inference before
registration, not inside an HTTP handler. No web button/background OCR worker added.

New output44 lines converted and passed through real candidate FastAPI TestClient +
temporary SQLite/W4.2 registration of PDF/image/raw/candidate; simulated reviewer appended
revision; app restart retained original result/history; authorized downloads returned exact
public bytes. This is in-process HTTP, NOT browser/TCP/production-authentication acceptance.

Developer commands from repository:
```
env -i PATH=/usr/local/bin:/usr/bin:/bin HOME=/tmp/mcis-image-ocr-live-20261116/home \
 PADDLE_PDX_CACHE_HOME=/workspace/mcis-paddleocr-trial/cache \
 /workspace/mcis-paddleocr-trial/venv/bin/python tools/image_review/run_public_page6.py \
 --model-root /workspace/mcis-paddleocr-trial/models \
 --image /workspace/mcis-paddleocr-handoff/source/page-6.png \
 --output /tmp/mcis-image-ocr-final-20261116
PYTHONPATH=service /workspace/mcis-pr104-supported-archive/service/.venv/bin/python \
 -m mcis_service.image_review.ppocr --raw /tmp/mcis-image-ocr-final-20261116/raw.json \
 --manifest /tmp/mcis-image-ocr-final-20261116/manifest.json \
 --output /tmp/mcis-image-ocr-final-20261116/fixture/candidates/ocr-page-6.candidate.json
```
Manifest copied from prior public page6 declaration, raw_sha256 replaced with THIS output's
computed digest, recognizer versions checked against run.json. Fresh fixture/source contains
copies of public PDF/page PNG; fixture/raw/ocr-page-6.json is this new result. Output paths
must be new; original public/historical files were not overwritten.

Selection with first newly generated output:
```
MCIS_PUBLIC_OCR_FIXTURE=/tmp/mcis-image-ocr-live-20261116/fixture PYTHONPATH=service \
 /workspace/mcis-pr104-supported-archive/service/.venv/bin/python -m pytest -q \
 service/tests/test_image_review_candidate.py service/tests/test_image_review_ppocr.py -rs
```
19 passed in3.36s (3 new synthetic adapter tests,16 candidate tests; not19 model calls).
Final repository-runner output rechecked with same command using final fixture and only
`service/tests/test_image_review_candidate.py::test_public_existing_output`:1 passed.
Overlapping test, do not add to19. Public sample test simulates human review, not human
certification. No previous restricted security/ECFC suites or browser launch retried.

## Developer visual spot check, not independent quality acceptance
Viewed original page image with local image viewer. Date2024年11月21, PSC2024年11月30,
and 缺陷0项 matched sampled output. VEGA DREAM/YANGZE22 spacing was lost in OCR:
output VEGADREAM/YANGZE22 vs original VEGA DREAM/YANGZE 22. Paragraphs span separate
lines, table is only individual text boxes, merged cells/blank cells not reconstructed.
No full CER/WER, tables, handwriting, stamps, poor-resolution or other-page quality claim.

## Deliverables / limitations
Local raw+run metadata: /tmp/mcis-image-ocr-final-20261116/{raw.json,run.json}; normalization
manifest and candidate under same root. Initial run/logs retained separately. No PDF, PNG,
raw OCR outputs, model weights, private material, DB or credential committed.
Default app remains disabled; no automatic web recognition, production identity, independent
acceptance, browser/visual interaction or archive restoration. All OCR remains pending human
review. Existing archive refusal preserved. Local artifacts needed for public integration test
are not in Git; absent fixture explicitly skips, never counts as real OCR success.
