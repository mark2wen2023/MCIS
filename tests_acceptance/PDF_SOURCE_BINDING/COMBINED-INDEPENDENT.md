# Independent review: combined internal PDF candidates

## Final local verification

From `pdf-combined-main`:

```
PYTHONPATH=tests_acceptance/PDF_TEXT_LAYER_CANDIDATE:tests_acceptance/PDF_SOURCE_BINDING ../mcis-work/service/.venv/bin/python -m pytest --import-mode=importlib -q tests_acceptance/PDF_TEXT_LAYER_CANDIDATE tests_acceptance/PDF_SOURCE_BINDING
```

**60 passed in 5.16 seconds** (31 text/lifecycle + 28 binding + 1 combined). The 31-case lifecycle suite is the reviewed 24-case base + original ownership regression (1) + lifecycle probes (6); the standalone ownership file also contains two redundant probes not added again to this total. These counts overlap the earlier suites; they are not 60 newly developed tests. No implementation edits by this reviewer.

Implementation byte identity checked against current isolated originals:
- derive.py: `39d57ffd056cd98d50d5743ec4ee809a05f1994f82b356c50befa8e15e381508`
- binding.py: `8be6ab85ef3987cb1185aa09aac0d3fefeac6873e1d98db0a3a0ee61c7f228c9`
- Included public PDF matches original official snapshot: `99084b8e672da6e2f8d9809bea25a92fe5fcf31c318554832e14339610015d7f`.

Original independent test files for text derivation and binding are identical. test_binding.py AND test_derive.py have only repository-relative source/deriver path adaptations. The original ownership regression is retained; two additional tests currently present in the standalone ownership file (SIGCHLD ignored and missing WNOWAIT) are covered equivalently in the combined six-case lifecycle file, not literally duplicated. That lifecycle file also checks remaining required capabilities and actual non-reaping observation -> group signal -> reap order.

## Combined test meaning

The extra integration test invokes the internal deriver on the public PDF, builds and validates the binding, then rejects a derivative with wrong source SHA. It checks caller dictionaries and original PDF unchanged. The `state` dictionary is synthetic and not passed to an ORM. It therefore does NOT verify real database currentSha256/custody transaction preservation. No registered/current source hash reconciliation or Change operation is performed.

## Verdict and restrictions

No blocker found for this internal content combination. This directory contains reports and the two tests_acceptance candidates, no runtime/PR97 implementation files. It is **not a Git checkout**: independent inspection here cannot certify actual main ancestry, remote state, or whole-repository runtime equality. Integration/patch verification against the real remote tree remains coordinator work. No remote, deployment, merge, real SSO/API, OCR, LLM or CI action performed.

Retain all lifecycle and trust limitations: exclusive child-reaper ownership required; no CPU/RSS or escaped-session sandbox; inherited environment and executable trust are not hardened. Binding hashes prove consistency, not authenticity or that a caller-supplied derivative truly came from the PDF. Host must use trusted extraction and current authorized source binding. Physical page numbers are not printed-page labels or complete image/text understanding.
