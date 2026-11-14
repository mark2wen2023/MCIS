# Independent opaque-upload metadata review

Reviewed new input-only bidi validation, client intake/legacy receipt distinction,
and OpaqueUploadStatus insertion against contracts/opaque-upload-metadata.md.
Reviewer changed only this acceptance directory; PR61/PR64 implementation untouched.

Commands:

```
service/.venv/bin/pytest -q -p no:cacheprovider tests_acceptance/OPAQUE_UPLOAD_METADATA/test_independent.py
web/node_modules/.bin/esbuild tests_acceptance/OPAQUE_UPLOAD_METADATA/frontend-independent.tsx --bundle --platform=node --format=cjs --jsx=automatic --alias:react=./web/node_modules/react --outfile=/tmp/opaque-upload-independent.cjs --log-level=warning
node /tmp/opaque-upload-independent.cjs
```

Results: **12 Python tests passed, zero skipped (3.80 s)**, one existing Starlette
httpx deprecation warning; final **32 frontend assertions passed**.

An initial code review found JavaScript `$` accepted a trailing newline in the intake
path, contrary to the exact-path contract. Implementer replaced it with a strict end
assertion and a type guard. Independent final tests cover LF/CR/CRLF endings and
wrong-type paths; all pass. No outstanding blocker found for this bounded slice.

Python uses explicit synthetic old-ingress simulation: temporarily allow the prior
filename rule while keeping actual preview/binding/commit/storage code. Then restore
current code, recover each of12 bidi-control filenames through the real read endpoint,
verify exact name and digest preservation with no added audit, and verify new replay
POST rejects422 without writes. This is a compatibility simulation, not evidence of
an authentic historical database or archive restoration run.

Frontend tests execute actual React server rendering and model functions. They cover
same-case exact-path selection, no disclosure for near-match/cross-case/malformed paths,
HTML injection escaping without media/script elements, ordinary Arabic/Chinese/emoji/
combining marks, all12 bidi controls blocked only on new input, a legacy parseReceipt
retaining its name, and wording requiring a receipt to verify registration outcome.

No media decoder, type inference, OCR/ASR, new network request, persistence or authority
was introduced in the reviewed diff. The disclosure describes the registration step
only; it does not conclude that downstream analysis never occurred. A path is a workflow
hint, not provenance or a verified successful receipt.

Limits: no browser-engine or disk-download test; React server rendering is not browser
execution. Existing filename UTF-16/codepoint length differences and legacy parsing rules
were not broadened by this slice. Browser sandbox failure was not bypassed. No deployment,
merge, real media/model capability claim or full-system acceptance claim.
