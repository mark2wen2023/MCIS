# Independent review: PDF/source binding pure contract

Final `binding.py` SHA256: `8be6ab85ef3987cb1185aa09aac0d3fefeac6873e1d98db0a3a0ee61c7f228c9`.

## Result

Command: `cd pdf-binding-candidate && ../mcis-work/service/.venv/bin/python -m pytest -q`

**28 passed in 1.52 seconds**: 16 author + 12 independent. No blocker found for retaining this pure internal contract candidate; not production integration approval.

Independent coverage: top-level bool/integer version confusion; float page/index byte-count rejection; extra Change fields at source/derivative/page levels; caller mutation isolation; rehashed outer artifact with stale derivative digest rejection; UTF-8 byte length versus character count; invalid surrogate JSON; harmless object key reordering; changed host registered hash rejection. Public-PDF author integration reran with the internal 53-physical-page text extractor and synthetic binding identities.

Author corrected Python dictionary equality (True == 1) to canonical-byte comparison during review, before independent first execution. The regression passed on first execution: there is **no claimed executed pre-fix failure**. Reviewer did not modify implementation.

## Essential boundaries

The independent self-consistent replacement-text test intentionally succeeds: anyone supplying new derivative text and corresponding hashes can construct a new consistent artifact. This layer does not prove text came from that PDF, authenticate the PDF, establish the operator, or verify sourceStateDigest against real storage. Formal integration must invoke a trusted deriver and acquire current authorized host binding; cannot accept artifact-supplied identity/version as authority.

No DB/custody operations, production API, actual case identities, LLM, CI, remote edits or deployment exercised. Input PDF bytes are not parsed by binding.py itself. Its schema/size checks do not establish hostile-input memory/CPU/depth sandboxing. Source hashes, derivative-content hash and whole-artifact hash serve distinct consistency purposes; registered and current source hash difference is preserved, not silently reconciled. Physical pages are not printed page labels; no OCR or image understanding claim.
