# Offline synthetic OCR producer static preflight

New isolated research directory on cd814e254cf715e9b64dc1f3250bcfd22c04f9a9. No service or existing public-page pin modifications. Repository guidance already read; no work in other task trees. No model libraries imported, initialized or executed, no network, install, download or real-document read.

## Existing entry is insufficient
At 91962113bd98778d3538f0e8e9879a014023c21f, tools/image_review/run_public_page6.py checks files and archive bytes then imports PaddleOCR and runs inference. It is hard-pinned to a different public page and is NOT a safe preflight or a producer for these synthetic images. It was read, never executed. The archive hashes here come unchanged from that runner's expected_models. Package versions come from tests_acceptance/image-ocr-local-run/REPORT.md at the same commit: paddlepaddle 3.2.0, paddleocr 3.3.2, paddlex 3.3.13. These are repository-recorded official-download pins; this turn did not newly authenticate the upstream publisher or fetch model archives.

## Operator command
Run with the already selected environment's Python (standard library only):

    python -I -B research/synthetic_ocr_producer_preflight/preflight.py --model-root /path/to/local/models --images /path/to/pinned/synthetic/renders
    python -I -B research/synthetic_ocr_producer_preflight/check.py

Preflight reads only fixed archive/model filenames and poppler-1.png/poppler-2.png under operator-selected roots. It streams archive SHA, inspects tar entries without extracting, and compares each regular member to readable extracted bytes. Required inference.json/inference.pdiparams/inference.yml must exist in the archive and match disk. Wrong hash, missing file/member, unreadability or invalid layout blocks. Source PNG hashes are the two unchanged cd814e synthetic-render pins; filenames or dimensions alone are insufficient.

importlib.metadata reads installed distribution metadata without importing paddle/paddleocr/paddlex. Only these three selected direct package versions are checked; no claim that transitive packages, native libraries, CPU kernels or ABI compatibility work. No new dependency lock is invented.

Exit 2 means blocked. Exit 0 means static_inputs_match_runtime_unverified, NOT ready for inference: readyForInference always remains false. Even perfect hashes and metadata do not prove a usable runtime or approved synthetic producer. The public-page runner cannot be repurposed by changing its pin in this task. There is no automatic fallback, retry, extraction, write, process launch or download in preflight.py.

## Actual tests and diagnosis
Seven test methods passed, exit 0. Controlled toy archives/extracted bytes and a non-image toy byte file exercise static positive, missing packages, wrong package version, changed archive/extracted/image bytes, missing required member and absent files. Test-only helper pins never enter the public CLI. The positive control explicitly stays readyForInference=false. Tests verify no Paddle modules entered sys.modules.

A separate real metadata read plus actual two pinned synthetic PNGs and an intentionally empty local model directory returned exit 2 (blocked.json). Current interpreter metadata lacks all three selected packages; both PNG hashes matched; both model archives were missing in that explicit empty root. This does NOT assert model absence elsewhere on the machine: no cache search or actual model loading was attempted.

Remaining gates: operator-supplied approved local model root; full dependency/native CPU compatibility; separately authorized safe synthetic producer and runtime initialization; trusted preprocessing/output provenance. No inference, model result, OCR score, production readiness, permissions or audit integration is claimed. Changing tool versions or acquiring missing packages/models needs separate authorization, not this CLI.
