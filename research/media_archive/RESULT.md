# Media archive research validation

Base: b1d2861037e893e4934fd45b6e7a0fe83a014c84, branch research/media-archive-contract.
Read sources: audio app/tasks at base; image app/tasks at91962113bd98778d3538f0e8e9879a014023c21f via Git. Default product is not modified.

Deliverables: contracts/media-archive-research-v1.md, offline member/index consistency prototype, fabricated fixtures generated in Python. No media/model/database files, no calls to OCR/ASR, no ordinary fixture presented as real recognition. Dummy original bytes deliberately are not decodable media; this checks structure/association only.

Command from repository root:
```
PYTHONPATH=. /workspace/mcis-pr104-supported-archive/service/.venv/bin/python -m pytest -q research/media_archive/test_contract.py --tb=short
```
Developer result:40 passed in0.06s. An initial collection failed because the new research package lacked __init__.py; the package marker was added before successful runs. No skipped tests; not independent acceptance, product regression, browser or production identity verification.

Checks: audio/image declarations; succeeded/failed/running_or_unknown/interrupted_unknown retained without execution; exact nonintegral sampling endpoint and unknown timing; missing source/result/version/history members; same-case graph; revision continuity; task/raw/candidate linkage; page declaration limits; missing audit lines; no unused member silently dropped; inputs unchanged by successful validation. These are ordinary fabricated contract examples, not previously restricted safety/ECFC tests.

Remaining: no product extractor, native machine artifact validation or full segment validation, proof of complete database inventory/unique revision-audit links, real media header/render verification, ZIP packaging, product file publication/transaction coordination, permission revalidation on future reads, or restoration. Contract explicitly identifies v2 without raw-output incompatibility. Historical receipts are documents only; restore_ready=false and execution_allowed=false remain unconditional. No export protection changed or production archive enabled.
