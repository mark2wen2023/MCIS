# Portable ECFC pending handoff — synthetic research only

Status: self-tested, pending independent acceptance. Fixed base: d1c1d378f8ec21e3cf8a01fe446df81770395a9e.
Only this new research package is added. No contracts, permissions, production storage, frozen corpus, 3D, model, service or UI changes.

## Reproduce
Use existing Python with jsonschema; no install or network is performed by these commands.
From any directory:
```bash
python -I -B /path/to/research/ecfc_pending_handoff/check.py --repo /path/to/MCIS
python -I -B /path/to/research/ecfc_pending_handoff/test_dependencies.py --repo /path/to/MCIS
```
All historical commits listed in DEPENDENCIES.json must exist locally; missing objects fail, never fetch. This candidate does not imply those commits are ancestors of the base.

Alternatively supply an explicitly prepared public-source export (not an internal work directory):
```bash
python -I -B /path/to/research/ecfc_pending_handoff/check.py --dependencies /path/to/export
python -I -B /path/to/research/ecfc_pending_handoff/test_dependencies.py --dependencies /path/to/export
```
Export layout is exactly `<export>/<full commit>/<repository path>` for the nine files in DEPENDENCIES.json. Obtain those files from mark2wen2023/MCIS at the listed commits through an authorized source. UTF-8 bytes/newlines must be unchanged. All nine Git blobs and both original JSON SHA-256 values are checked before imports. No old modules or trajectory originals are committed in this package. The loader temporarily materializes verified public files for the unchanged original test's sibling import and removes them on exit; a writable temporary directory is needed. No bytecode is written with -B.

## What runs
Actual pinned e0cbccc receiver + original three tests; actual d1c1d37 locate function, only ROOT rebound to synthetic source folders; original projection/validator/host modules and fixed 2048c60 original bytes.
Two downstream cases: observation-only leaves link evidence insufficient; two opposing source statements leave the link in conflicting-assertions/pending review. Four invalid inputs are rejected. Source statement stance is a quoted source assertion, never an adjudicated truth or a blind-review answer.
Event and candidate-link references remain separate. No definite causation, human signature or jump anchor. T100 missing heading and T124.250 gap/no-observation remain unchanged. Synthetic statements are new research attachments for SYN-XREPO-001, not facts contained in the original trajectory files.

## Validation limits
These are real pure-module executions with synthetic adapter input, NOT real registration, ECFC node/link database readback, production authority, semantic accuracy, or human approval. The pure projection consumes test-wrapper-resolved statements, not arbitrary public requests; it is not an authorization boundary.
No heldout/answer data is present or read. Source hashes show reproducibility, not truth. Candidate remains unmerged/undeployed. See VALIDATION.md for actual commands and results.
