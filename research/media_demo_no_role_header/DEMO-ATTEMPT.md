# Synthetic loopback demo attempt — incomplete browser acceptance

2026-11-18, code d6835d995dd35b539dbad0543511b4b23ee507c7 over6bd0bd87271ad7aa2ff073b42f51dc6ce345e400. Only generated schematic PDF/PNG, fabricated OCR/draft and440Hz tone; no original case/model/credential used. Formal archive/restore remain disabled.

From repository root with PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.:service and /workspace/mcis-pr104-supported-archive/service/.venv/bin/python:
1. `-m tools.media_review_demo.prepare --parent /tmp` completed with status prepared, modelExecuted=false, browserVerified=false, archiveSupported=false. Fresh directory /tmp/mcis-media-demo-mc02jghu; no prior DB reused. Preparation used existing default Investigator, no role header.
2. `-m tools.media_review_demo.launch --root /tmp/mcis-media-demo-mc02jghu --manifest /tmp/mcis-media-demo-mc02jghu/demo-manifest.json` passed metadata preflight. sourceBytesVerified=false.
3. Same launcher with `--serve` started Uvicorn PID889 on127.0.0.1:8766, application startup complete. Both runtime slots are checked None by launcher. No outward bind or production configuration changes.

Case MEDIA-DEMO-SYNTHETIC; image run OCR-dffaba1c8b9a4ef29a41909d7f754ff8; audio run AR-46f52555360e4fb789b49977b1c1c6cd. Preparation includes in-process API readback, not browser acceptance.

Browser tool discovery offered no usable desktop JavaScript control despite remote_desktop enabled/unknown. Existing Chromium156.0.8078.79 was attempted normally:
`chromium --headless --dump-dom --user-data-dir=/tmp/mcis-browser-synthetic-check http://127.0.0.1:8766/image-review-lab`
Exit134. Crashpad reported missing database, followed by fatal SUID sandbox helper configuration error. Chromium explicitly aborted rather than running without sandboxing. No page DOM or interaction obtained. This is a browser/environment failure, not an HTTP403 or automatic tool-review denial. No retry, alternative browser/tool, sandbox disablement, permissions change or dependency installation was attempted.

Stopped browser validation immediately. Sent SIGINT to this attempt's exact Uvicorn PID889 and confirmed graceful shutdown. Synthetic data remains locally; no deletion/retry of unknown objects. No media/database/profile artifacts included in Git.

Actual completion: new synthetic preparation, metadata preflight, actual loopback service startup/shutdown. Prior single new ordinary synthetic test passed1/1 in0.77s; not rerun here. NOT completed: real browser rendering, playback/hearing, UI manual review/save/reload, network-level end-to-end review, independent acceptance. No claim of a closed end-to-end demo. Resolve supported browser environment configuration through normal administration before further browser acceptance; do not bypass sandbox.
